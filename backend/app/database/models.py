"""Relational schema. Reserved tables do not imply completed analysis features."""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON, Boolean, CheckConstraint, DateTime, Float, ForeignKey, ForeignKeyConstraint,
    Index, Integer, MetaData, String, Text, UniqueConstraint, Uuid, func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention={
        "ix": "ix_%(table_name)s_%(column_0_name)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    })


class Timestamps:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Owned(Timestamps):
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)


class InvestigationOwned(Owned):
    investigation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)


def owned_constraints(*constraints):
    return (UniqueConstraint("id", "owner_id"), *constraints)


def investigation_constraints(*constraints):
    return owned_constraints(
        ForeignKeyConstraint(["investigation_id", "owner_id"], ["investigations.id", "investigations.owner_id"], ondelete="CASCADE"),
        *constraints,
    )


class User(Timestamps, Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    # IDs originate exclusively from verified Supabase tokens, never a seed script.
    investigations: Mapped[list["Investigation"]] = relationship(back_populates="owner", passive_deletes=True)


class UserProfile(Owned, Base):
    __tablename__ = "user_profiles"
    __table_args__ = owned_constraints(UniqueConstraint("owner_id"))
    locale: Mapped[str | None] = mapped_column(String(32))
    alert_preferences: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class Device(Owned, Base):
    __tablename__ = "devices"
    __table_args__ = owned_constraints(CheckConstraint("platform IN ('android','web')", name="platform"))
    platform: Mapped[str] = mapped_column(String(16), nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserConsent(Owned, Base):
    __tablename__ = "user_consents"
    __table_args__ = owned_constraints(UniqueConstraint("owner_id", "purpose"))
    purpose: Mapped[str] = mapped_column(String(80), nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    policy_version: Mapped[str] = mapped_column(String(80), nullable=False)


class Investigation(Owned, Base):
    __tablename__ = "investigations"
    __table_args__ = owned_constraints(
        CheckConstraint("subject_type IN ('sms','url','apk','qr','caller')", name="subject_type"),
        CheckConstraint("status IN ('queued','running','completed','partial','failed')", name="status"),
        ForeignKeyConstraint(["device_id", "owner_id"], ["devices.id", "devices.owner_id"]),
        Index("ix_investigations_owner_created", "owner_id", "created_at", "id"),
    )
    subject_type: Mapped[str] = mapped_column(String(16), nullable=False)
    subject_value: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    device_id: Mapped[UUID | None] = mapped_column(Uuid)
    result: Mapped[dict] = mapped_column(JSON, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    owner: Mapped[User] = relationship(back_populates="investigations", foreign_keys="Investigation.owner_id")
    events: Mapped[list["InvestigationEvent"]] = relationship(viewonly=True, foreign_keys="[InvestigationEvent.investigation_id, InvestigationEvent.owner_id]")
    evidence: Mapped[list["Evidence"]] = relationship(viewonly=True, foreign_keys="[Evidence.investigation_id, Evidence.owner_id]")


class InvestigationEvent(InvestigationOwned, Base):
    __tablename__ = "investigation_events"
    __table_args__ = investigation_constraints()
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class EvidenceSource(InvestigationOwned, Base):
    __tablename__ = "evidence_sources"
    __table_args__ = investigation_constraints()
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    reference: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Evidence(InvestigationOwned, Base):
    __tablename__ = "evidence"
    __table_args__ = investigation_constraints(
        ForeignKeyConstraint(["source_id", "owner_id"], ["evidence_sources.id", "evidence_sources.owner_id"]),
        CheckConstraint("severity IN ('info','caution','high')", name="severity"),
    )
    source_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(40), nullable=False)
    attributes: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Domain(Owned, Base):
    __tablename__ = "domains"
    __table_args__ = owned_constraints(UniqueConstraint("owner_id", "hostname"))
    hostname: Mapped[str] = mapped_column(String(253), nullable=False)


class URLIndicator(InvestigationOwned, Base):
    __tablename__ = "urls"
    __table_args__ = investigation_constraints(
        UniqueConstraint("investigation_id", "sha256"),
        Index("ix_urls_owner_sha256_investigation", "owner_id", "sha256", "investigation_id"),
        Index("ix_urls_owner_domain_investigation", "owner_id", "domain_id", "investigation_id"),
        ForeignKeyConstraint(["domain_id", "owner_id"], ["domains.id", "domains.owner_id"]),
    )
    domain_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    redacted_value: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class Application(Owned, Base):
    __tablename__ = "applications"
    __table_args__ = owned_constraints(UniqueConstraint("owner_id", "package_name"))
    package_name: Mapped[str] = mapped_column(String(255), nullable=False)
    app_name: Mapped[str | None] = mapped_column(String(255))


class APKAnalysis(InvestigationOwned, Base):
    __tablename__ = "apk_analysis"
    __table_args__ = investigation_constraints(
        ForeignKeyConstraint(["application_id", "owner_id"], ["applications.id", "applications.owner_id"]),
    )
    application_id: Mapped[UUID | None] = mapped_column(Uuid)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    static_metadata: Mapped[dict] = mapped_column(JSON, nullable=False)


class PhoneIndicator(Owned, Base):
    __tablename__ = "phone_indicators"
    __table_args__ = owned_constraints(UniqueConstraint("owner_id", "e164"))
    e164: Mapped[str] = mapped_column(String(16), nullable=False)


class QRAnalysis(InvestigationOwned, Base):
    __tablename__ = "qr_analyses"
    __table_args__ = investigation_constraints()
    content_type: Mapped[str] = mapped_column(String(32), nullable=False)
    redacted_content: Mapped[str] = mapped_column(Text, nullable=False)
    decoded_attributes: Mapped[dict] = mapped_column(JSON, nullable=False)


class ModelVersion(Timestamps, Base):
    __tablename__ = "model_versions"
    __table_args__ = (UniqueConstraint("name", "version"),)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(100), nullable=False)
    task: Mapped[str] = mapped_column(String(80), nullable=False)
    artifact_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    dataset_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    provenance: Mapped[dict] = mapped_column(JSON, nullable=False)
    evaluation: Mapped[dict] = mapped_column(JSON, nullable=False)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ModelPrediction(InvestigationOwned, Base):
    __tablename__ = "model_predictions"
    __table_args__ = investigation_constraints()
    model_version_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("model_versions.id"), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(32), nullable=False)
    decision_score: Mapped[float | None] = mapped_column(Float)
    score_type: Mapped[str | None] = mapped_column(String(64))
    inferred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ThreatIntelligenceResult(InvestigationOwned, Base):
    __tablename__ = "threat_intelligence_results"
    __table_args__ = investigation_constraints(
        ForeignKeyConstraint(["source_id", "owner_id"], ["evidence_sources.id", "evidence_sources.owner_id"]),
    )
    source_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    verdict: Mapped[str | None] = mapped_column(String(32))
    details: Mapped[dict] = mapped_column(JSON, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RiskAssessment(InvestigationOwned, Base):
    __tablename__ = "risk_assessments"
    __table_args__ = investigation_constraints(
        UniqueConstraint("investigation_id"),
        CheckConstraint("classification IN ('SAFE_INDICATORS','EXERCISE_CAUTION','HIGH_RISK','CONFIRMED_FRAUD')", name="classification"),
        CheckConstraint("risk_score IS NULL OR (risk_score >= 0 AND risk_score <= 100)", name="score_range"),
        CheckConstraint("(risk_score IS NULL AND score_type IS NULL) OR (risk_score IS NOT NULL AND score_type IS NOT NULL)", name="score_type"),
        CheckConstraint("classification <> 'CONFIRMED_FRAUD' OR (human_reviewed_at IS NOT NULL AND authoritative_evidence_id IS NOT NULL)", name="confirmed_review"),
        ForeignKeyConstraint(["authoritative_evidence_id", "owner_id"], ["evidence.id", "evidence.owner_id"]),
    )
    classification: Mapped[str] = mapped_column(String(32), nullable=False)
    risk_score: Mapped[float | None] = mapped_column(Float)
    score_type: Mapped[str | None] = mapped_column(String(64))
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    methodology_version: Mapped[str] = mapped_column(String(80), nullable=False)
    missing_information: Mapped[list] = mapped_column(JSON, nullable=False)
    human_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    authoritative_evidence_id: Mapped[UUID | None] = mapped_column(Uuid)


class GraphNode(Owned, Base):
    __tablename__ = "graph_nodes"
    __table_args__ = owned_constraints(UniqueConstraint("owner_id", "node_type", "value_sha256"))
    node_type: Mapped[str] = mapped_column(String(32), nullable=False)
    redacted_value: Mapped[str] = mapped_column(Text, nullable=False)
    value_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    attributes: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class GraphEdge(InvestigationOwned, Base):
    __tablename__ = "graph_edges"
    __table_args__ = investigation_constraints(
        ForeignKeyConstraint(["from_node_id", "owner_id"], ["graph_nodes.id", "graph_nodes.owner_id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["to_node_id", "owner_id"], ["graph_nodes.id", "graph_nodes.owner_id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["evidence_id", "owner_id"], ["evidence.id", "evidence.owner_id"], ondelete="CASCADE"),
        UniqueConstraint("investigation_id", "from_node_id", "to_node_id", "relationship_type", "evidence_id"),
        CheckConstraint("from_node_id <> to_node_id", name="no_self_edge"),
    )
    from_node_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    to_node_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    evidence_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(64), nullable=False)


class CommunityReport(Owned, Base):
    __tablename__ = "community_reports"
    __table_args__ = owned_constraints(CheckConstraint("moderation_status IN ('unreviewed','approved','rejected')", name="moderation_status"))
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False)
    redacted_subject: Mapped[str] = mapped_column(Text, nullable=False)
    redacted_description: Mapped[str] = mapped_column(Text, nullable=False)
    moderation_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unreviewed")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Watchlist(Owned, Base):
    __tablename__ = "watchlists"
    __table_args__ = owned_constraints(UniqueConstraint("owner_id", "indicator_type", "value_sha256"))
    indicator_type: Mapped[str] = mapped_column(String(32), nullable=False)
    redacted_value: Mapped[str] = mapped_column(Text, nullable=False)
    value_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class SecurityAlert(InvestigationOwned, Base):
    __tablename__ = "security_alerts"
    __table_args__ = investigation_constraints(CheckConstraint("severity IN ('info','caution','high')", name="severity"))
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(Owned, Base):
    __tablename__ = "audit_logs"
    __table_args__ = owned_constraints()
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_id: Mapped[UUID | None] = mapped_column(Uuid)
    # No input text, bearer tokens, full request URLs or provider keys.
    request_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)


class ProviderStatus(Timestamps, Base):
    __tablename__ = "provider_status"
    provider: Mapped[str] = mapped_column(String(80), primary_key=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class APIRateLimitBucket(Timestamps, Base):
    """Internal actual request counters, not dashboard statistics."""
    __tablename__ = "api_rate_limit_buckets"
    __table_args__ = (CheckConstraint("request_count >= 1", name="positive_count"),)
    key_sha256: Mapped[str] = mapped_column(String(64), primary_key=True)
    window_start: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False)
