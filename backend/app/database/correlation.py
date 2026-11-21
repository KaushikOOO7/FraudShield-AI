"""Owner-scoped correlation of actual persisted URL observations, in one transaction."""
import hashlib
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from backend.app.core.errors import APIError
from backend.app.database import models
from backend.app.graph.network import build_correlation
from backend.app.schemas.correlation import CorrelationEdge, CorrelationNode, URLObservation
from backend.app.schemas.investigation import EvidenceSource


class CorrelationRepository:
    def __init__(self, session, owner_id: UUID):
        if session.info.get("owner_id") != owner_id:
            raise APIError(403, "ownership_error", "Database ownership context does not match")
        self.session = session
        self.owner_id = owner_id

    def _insert_once(self, model, values):
        insert = sqlite_insert if self.session.bind.dialect.name == "sqlite" else pg_insert
        self.session.execute(insert(model).values(**values).on_conflict_do_nothing())

    def _node(self, kind, value, digest):
        node_id = uuid5(NAMESPACE_URL, f"fraudshield:graph:{self.owner_id}:{kind}:{digest}")
        self._insert_once(models.GraphNode, dict(
            id=node_id, owner_id=self.owner_id, node_type=kind, redacted_value=value,
            value_sha256=digest, attributes={},
        ))
        row = self.session.scalar(select(models.GraphNode).where(
            models.GraphNode.owner_id == self.owner_id, models.GraphNode.node_type == kind,
            models.GraphNode.value_sha256 == digest,
        ))
        if row is None:
            raise APIError(409, "graph_storage_conflict", "Graph identity could not be persisted")
        return CorrelationNode(id=row.id, type=kind, value=row.redacted_value)

    def correlate(self, root_id: UUID, limit: int, request_id: UUID):
        now = datetime.now(timezone.utc)
        root = self.session.scalar(select(models.Investigation).where(
            models.Investigation.id == root_id, models.Investigation.owner_id == self.owner_id,
            models.Investigation.expires_at > now,
        ))
        if root is None:
            raise APIError(404, "investigation_not_found", "Investigation was not found")
        root_urls = self.session.scalars(select(models.URLIndicator).where(
            models.URLIndicator.investigation_id == root_id, models.URLIndicator.owner_id == self.owner_id,
        )).all()
        related, has_more, observations, sources = [], False, [], []
        node_map, edge_map = {}, {}
        if root_urls:
            hashes = {item.sha256 for item in root_urls}
            domains = {item.domain_id for item in root_urls}
            match = or_(models.URLIndicator.sha256.in_(hashes), models.URLIndicator.domain_id.in_(domains))
            observed = select(models.URLIndicator.id).where(
                models.URLIndicator.investigation_id == models.Investigation.id,
                models.URLIndicator.owner_id == self.owner_id, match,
            ).exists()
            candidates = self.session.scalars(select(models.Investigation).where(
                models.Investigation.owner_id == self.owner_id, models.Investigation.id != root_id,
                models.Investigation.expires_at > now, models.Investigation.subject_type.in_(("sms", "url", "qr", "apk")), observed,
            ).order_by(models.Investigation.created_at.desc(), models.Investigation.id.desc()).limit(limit + 1)).all()
            has_more = len(candidates) > limit
            related = candidates[:limit]
            cases = {case.id: case for case in [root, *related]}
            rows = self.session.execute(select(models.URLIndicator, models.Domain).join(
                models.Domain, (models.Domain.id == models.URLIndicator.domain_id) & (models.Domain.owner_id == models.URLIndicator.owner_id),
            ).where(
                models.URLIndicator.owner_id == self.owner_id, models.URLIndicator.investigation_id.in_(cases), match,
            ).order_by(models.URLIndicator.investigation_id, models.URLIndicator.sha256)).all()
            for indicator, domain in rows:
                case = cases[indicator.investigation_id]
                observed_at = case.created_at.replace(tzinfo=timezone.utc) if case.created_at.tzinfo is None else case.created_at
                source_id = uuid5(NAMESPACE_URL, f"fraudshield:observations:{self.owner_id}:{case.id}:v1")
                if not any(source.id == source_id for source in sources):
                    source = EvidenceSource(
                        id=source_id, name="stored-url-observations-v1", kind="rule", status="completed",
                        reference="docs/CORRELATION.md", observed_at=observed_at,
                    )
                    self._insert_once(models.EvidenceSource, dict(
                        id=source.id, owner_id=self.owner_id, investigation_id=case.id, name=source.name,
                        kind=source.kind, status=source.status, reference=source.reference, observed_at=source.observed_at,
                    ))
                    sources.append(source)
                evidence_id = uuid5(NAMESPACE_URL, f"fraudshield:url-observation:{self.owner_id}:{indicator.id}:v1")
                self._insert_once(models.Evidence, dict(
                    id=evidence_id, owner_id=self.owner_id, investigation_id=case.id, source_id=source_id,
                    code="STORED_URL_OBSERVATION", description="The investigation stored this parsed URL and its exact hostname. This observation does not establish reputation or ownership.",
                    severity="info", verification_status="documented_rule", observed_at=observed_at,
                    attributes={"url_indicator_id": str(indicator.id), "redacted_url": indicator.redacted_value, "domain": domain.hostname},
                ))
                case_node = self._node("investigation", str(case.id), hashlib.sha256(str(case.id).encode()).hexdigest())
                url_node = self._node("url", indicator.redacted_value, indicator.sha256)
                domain_node = self._node("domain", domain.hostname, hashlib.sha256(domain.hostname.encode()).hexdigest())
                for node in (case_node, url_node, domain_node):
                    node_map[node.id] = node
                observations.append(URLObservation(
                    evidence_id=evidence_id, source_id=source_id, investigation_id=case.id,
                    url_indicator_id=indicator.id, url_node_id=url_node.id, domain_node_id=domain_node.id,
                    redacted_url=indicator.redacted_value, domain=domain.hostname, observed_at=observed_at,
                ))
                for origin, target, relationship in ((case_node, url_node, "observed_url"), (url_node, domain_node, "url_host")):
                    edge_id = uuid5(NAMESPACE_URL, f"fraudshield:edge:{self.owner_id}:{evidence_id}:{relationship}:{origin.id}:{target.id}")
                    self._insert_once(models.GraphEdge, dict(
                        id=edge_id, owner_id=self.owner_id, investigation_id=case.id,
                        from_node_id=origin.id, to_node_id=target.id, evidence_id=evidence_id, relationship_type=relationship,
                    ))
                    edge_map[edge_id] = CorrelationEdge(
                        id=edge_id, from_node_id=origin.id, to_node_id=target.id, relationship=relationship,
                        investigation_id=case.id, evidence_id=evidence_id,
                    )
        result = build_correlation(root_id, [root, *related], list(node_map.values()), list(edge_map.values()), observations, sources, limit, has_more)
        self.session.add(models.InvestigationEvent(
            owner_id=self.owner_id, investigation_id=root_id, event_type="correlation.completed",
            details={"methodology_version": result.methodology_version, "status": result.status, "related_count": len(result.related_investigations), "has_more": has_more},
        ))
        self.session.add(models.AuditLog(owner_id=self.owner_id, action="investigation.correlated", resource_id=root_id, request_id=request_id))
        self.session.flush()
        return result
