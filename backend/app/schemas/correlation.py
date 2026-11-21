from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from backend.app.schemas.investigation import ContractModel, EvidenceSource


class CorrelationNode(ContractModel):
    id: UUID
    type: Literal["investigation", "url", "domain"]
    value: str = Field(max_length=16384)


class CorrelationEdge(ContractModel):
    id: UUID
    from_node_id: UUID
    to_node_id: UUID
    relationship: Literal["observed_url", "url_host"]
    investigation_id: UUID
    evidence_id: UUID


class URLObservation(ContractModel):
    evidence_id: UUID
    source_id: UUID
    investigation_id: UUID
    url_indicator_id: UUID
    url_node_id: UUID
    domain_node_id: UUID
    redacted_url: str = Field(max_length=16384)
    domain: str = Field(max_length=253)
    observed_at: datetime
    verification_status: Literal["documented_rule"] = "documented_rule"


class RelatedInvestigation(ContractModel):
    investigation_id: UUID
    subject_type: Literal["sms", "url", "qr", "apk"]
    source: str
    created_at: datetime
    shared_url_node_ids: list[UUID]
    shared_domain_node_ids: list[UUID]


class CorrelationResponse(ContractModel):
    investigation_id: UUID
    status: Literal["matched", "no_matches", "no_identifiers"]
    methodology_version: Literal["observed-identifiers-v2"] = "observed-identifiers-v2"
    generated_at: datetime
    related_investigations: list[RelatedInvestigation]
    nodes: list[CorrelationNode]
    edges: list[CorrelationEdge]
    observations: list[URLObservation]
    sources: list[EvidenceSource]
    limit: int = Field(ge=1, le=100)
    has_more: bool
    limitations: list[str]

    @model_validator(mode="after")
    def evidence_backed_graph(self):
        nodes = {node.id: node for node in self.nodes}
        evidence = {item.evidence_id: item for item in self.observations}
        sources = {source.id for source in self.sources}
        if len(nodes) != len(self.nodes) or len(evidence) != len(self.observations):
            raise ValueError("Graph identifiers must be unique")
        if len(sources) != len(self.sources) or len({edge.id for edge in self.edges}) != len(self.edges):
            raise ValueError("Graph sources and edges must be unique")
        for item in self.observations:
            if item.source_id not in sources:
                raise ValueError("Observation references an absent source")
            if item.url_node_id not in nodes or nodes[item.url_node_id].type != "url":
                raise ValueError("Observation references an absent URL node")
            if item.domain_node_id not in nodes or nodes[item.domain_node_id].type != "domain":
                raise ValueError("Observation references an absent domain node")
        for edge in self.edges:
            if edge.from_node_id not in nodes or edge.to_node_id not in nodes:
                raise ValueError("Edge references an absent node")
            observation = evidence.get(edge.evidence_id)
            if observation is None or observation.investigation_id != edge.investigation_id:
                raise ValueError("Edge requires evidence from its investigation")
            if edge.relationship == "observed_url":
                origin = nodes[edge.from_node_id]
                if origin.type != "investigation" or origin.value != str(edge.investigation_id) or edge.to_node_id != observation.url_node_id:
                    raise ValueError("Observed-URL edge does not match its evidence")
            elif edge.from_node_id != observation.url_node_id or edge.to_node_id != observation.domain_node_id:
                raise ValueError("URL-host edge does not match its evidence")
        for related in self.related_investigations:
            if related.investigation_id == self.investigation_id:
                raise ValueError("Root cannot be its own related investigation")
            for ids, kind in ((related.shared_url_node_ids, "url"), (related.shared_domain_node_ids, "domain")):
                for identifier in ids:
                    if identifier not in nodes or nodes[identifier].type != kind:
                        raise ValueError("Related match references an absent identifier")
                    supporting = {item.investigation_id for item in self.observations if (item.url_node_id if kind == "url" else item.domain_node_id) == identifier}
                    if not {self.investigation_id, related.investigation_id}.issubset(supporting):
                        raise ValueError("Shared identifier requires observations from both investigations")
            if not related.shared_url_node_ids and not related.shared_domain_node_ids:
                raise ValueError("Related investigation has no observed shared identifier")
        expected = "matched" if self.related_investigations else "no_matches" if self.observations else "no_identifiers"
        if self.status != expected:
            raise ValueError("Correlation status must reflect observed matches")
        return self
