import hashlib
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import delete, exists, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from backend.app.core.errors import APIError
from backend.app.database import models
from backend.app.database.graph_cleanup import prune_orphan_graph_nodes
from backend.app.schemas.investigation import InvestigationList, InvestigationResponse
from backend.app.services.bundle import InvestigationBundle
from backend.app.utils.privacy import redact_url


class InvestigationRepository:
    def __init__(self, session, owner_id: UUID):
        if session.info.get("owner_id") != owner_id:
            raise APIError(403, "ownership_error", "Database ownership context does not match")
        self.session = session
        self.owner_id = owner_id

    def _insert(self, model):
        return sqlite_insert(model) if self.session.bind.dialect.name == "sqlite" else pg_insert(model)

    def check_device(self, device_id: UUID | None):
        if device_id is not None and self.session.scalar(select(models.Device.id).where(models.Device.id == device_id, models.Device.owner_id == self.owner_id)) is None:
            raise APIError(404, "device_not_found", "Device is not registered to this user")

    def _audit(self, action: str, resource_id: UUID | None, request_id: UUID):
        self.session.add(models.AuditLog(owner_id=self.owner_id, action=action, resource_id=resource_id, request_id=request_id))

    def _model_version(self, manifest: dict) -> UUID:
        model_id = uuid5(NAMESPACE_URL, f"fraudshield:model:{manifest['name']}:{manifest['version']}:{manifest['artifact_sha256']}")
        statement = self._insert(models.ModelVersion).values(
            id=model_id, name=manifest["name"], version=manifest["version"], task=manifest["task"],
            artifact_sha256=manifest["artifact_sha256"], dataset_sha256=manifest["dataset"]["file_sha256"],
            provenance=manifest["dataset"], evaluation=manifest["evaluation"],
            trained_at=datetime.fromisoformat(manifest["trained_at"]),
        ).on_conflict_do_nothing(index_elements=[models.ModelVersion.name, models.ModelVersion.version])
        self.session.execute(statement)
        actual = self.session.scalar(select(models.ModelVersion).where(models.ModelVersion.name == manifest["name"], models.ModelVersion.version == manifest["version"]))
        if actual is None or actual.artifact_sha256 != manifest["artifact_sha256"]:
            raise APIError(409, "model_version_conflict", "Model version does not match its registered artifact")
        return actual.id

    def create(self, bundle: InvestigationBundle, submission, request_id: UUID) -> InvestigationResponse:
        response = bundle.response
        self.session.add(models.Investigation(
            id=response.investigation_id, owner_id=self.owner_id, subject_type=response.subject.type,
            subject_value=response.subject.value or "", source=submission.source, status=response.status,
            device_id=submission.device_id, result=response.model_dump(mode="json"),
            created_at=response.created_at, expires_at=response.expires_at,
        ))
        self.session.flush()
        for source in response.sources:
            self.session.add(models.EvidenceSource(
                id=source.id, owner_id=self.owner_id, investigation_id=response.investigation_id,
                name=source.name, kind=source.kind, reference=source.reference, status=source.status,
                observed_at=source.observed_at,
            ))
        self.session.flush()
        for finding in response.findings:
            self.session.add(models.Evidence(
                id=finding.id, owner_id=self.owner_id, investigation_id=response.investigation_id,
                source_id=finding.source_id, code=finding.code, description=finding.description,
                severity=finding.severity, verification_status=finding.verification_status,
                attributes=finding.attributes, observed_at=finding.observed_at,
            ))
        self.session.flush()
        for model in response.models:
            if model.status == "available":
                manifest = bundle.model_manifests.get(model.name) or bundle.model_manifest
                if manifest is None or manifest["version"] != model.version or manifest["name"] != model.name:
                    raise APIError(500, "model_provenance_missing", "Prediction provenance is unavailable")
                model_version_id = self._model_version(manifest)
                self.session.add(models.ModelPrediction(
                    owner_id=self.owner_id, investigation_id=response.investigation_id,
                    model_version_id=model_version_id, label=model.label, decision_score=model.decision_score,
                    score_type=model.score_type, inferred_at=model.observed_at,
                ))
        for parsed in bundle.urls:
            self.session.execute(self._insert(models.Domain).values(owner_id=self.owner_id, hostname=parsed.hostname).on_conflict_do_nothing(index_elements=[models.Domain.owner_id, models.Domain.hostname]))
            domain_id = self.session.scalar(select(models.Domain.id).where(models.Domain.owner_id == self.owner_id, models.Domain.hostname == parsed.hostname))
            self.session.add(models.URLIndicator(
                owner_id=self.owner_id, investigation_id=response.investigation_id,
                domain_id=domain_id, redacted_value=redact_url(parsed.normalized),
                sha256=hashlib.sha256(parsed.normalized.encode()).hexdigest(),
            ))
        for source_id, outcome in bundle.provider_results:
            self.session.add(models.ThreatIntelligenceResult(
                owner_id=self.owner_id, investigation_id=response.investigation_id, source_id=source_id,
                provider=outcome.provider, status=outcome.status, verdict=outcome.verdict,
                details=outcome.model_dump(mode="json"), observed_at=outcome.checked_at,
            ))
            if outcome.status not in ("provider_not_configured", "not_requested", "unsupported_input"):
                successful = outcome.status in ("matched", "no_match", "stale", "observed")
                values = {"provider": outcome.provider, "status": outcome.status}
                if successful:
                    values["last_success_at"] = outcome.checked_at
                elif outcome.status not in ("not_found",):
                    values["last_error_at"] = outcome.checked_at
                self.session.execute(self._insert(models.ProviderStatus).values(**values).on_conflict_do_update(index_elements=[models.ProviderStatus.provider], set_={"updated_at": func.now(), **{key: value for key, value in values.items() if key != "provider"}}))
        assessment = response.assessment
        if bundle.qr_analysis is not None:
            self.session.add(models.QRAnalysis(owner_id=self.owner_id, investigation_id=response.investigation_id, **bundle.qr_analysis))
        if bundle.apk_analysis is not None:
            self.session.add(models.APKAnalysis(owner_id=self.owner_id, investigation_id=response.investigation_id, **bundle.apk_analysis))
        profile = self.session.scalar(select(models.UserProfile).where(models.UserProfile.owner_id == self.owner_id))
        if assessment.classification == "HIGH_RISK" and profile is not None and profile.alert_preferences.get("high_risk_alerts") is True:
            self.session.add(models.SecurityAlert(
                owner_id=self.owner_id, investigation_id=response.investigation_id,
                severity="high", message=assessment.explanation,
            ))
        self.session.add(models.RiskAssessment(
            owner_id=self.owner_id, investigation_id=response.investigation_id,
            classification=assessment.classification, risk_score=assessment.risk_score,
            score_type=assessment.score_type, explanation=assessment.explanation,
            methodology_version=assessment.methodology_version, missing_information=assessment.missing_information,
        ))
        self.session.add(models.InvestigationEvent(
            owner_id=self.owner_id, investigation_id=response.investigation_id, event_type="analysis.completed",
            details={"source": submission.source, "external_intelligence_requested": submission.use_threat_intelligence, "status": response.status},
        ))
        self._audit("investigation.created", response.investigation_id, request_id)
        self.session.flush()
        return response

    def get(self, investigation_id: UUID, request_id: UUID) -> InvestigationResponse:
        row = self.session.scalar(select(models.Investigation).where(
            models.Investigation.id == investigation_id, models.Investigation.owner_id == self.owner_id,
            models.Investigation.expires_at > datetime.now(timezone.utc),
        ))
        if row is None:
            raise APIError(404, "investigation_not_found", "Investigation was not found")
        self._audit("investigation.read", row.id, request_id)
        return InvestigationResponse.model_validate(row.result)

    def list(self, limit: int, offset: int, request_id: UUID) -> InvestigationList:
        rows = self.session.scalars(select(models.Investigation).where(
            models.Investigation.owner_id == self.owner_id,
            models.Investigation.expires_at > datetime.now(timezone.utc),
        ).order_by(models.Investigation.created_at.desc(), models.Investigation.id.desc()).offset(offset).limit(limit + 1)).all()
        self._audit("investigation.listed", None, request_id)
        return InvestigationList(items=[InvestigationResponse.model_validate(row.result) for row in rows[:limit]], limit=limit, offset=offset, has_more=len(rows) > limit)

    def delete(self, investigation_id: UUID, request_id: UUID):
        row = self.session.scalar(select(models.Investigation).where(models.Investigation.id == investigation_id, models.Investigation.owner_id == self.owner_id))
        if row is None:
            raise APIError(404, "investigation_not_found", "Investigation was not found")
        self.session.delete(row)
        self.session.flush()
        prune_orphan_graph_nodes(self.session, self.owner_id)
        self.session.execute(delete(models.Domain).where(
            models.Domain.owner_id == self.owner_id,
            ~exists(select(models.URLIndicator.id).where(models.URLIndicator.domain_id == models.Domain.id)),
        ))
        self._audit("investigation.deleted", investigation_id, request_id)
        self.session.flush()
