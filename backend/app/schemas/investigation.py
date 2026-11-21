from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Subject(ContractModel):
    type: Literal["sms", "url", "apk", "qr", "caller"]
    value: str | None = Field(max_length=5000)
    attributes: dict[str, JsonValue] = Field(default_factory=dict)


class EvidenceSource(ContractModel):
    id: UUID
    name: str = Field(max_length=100)
    kind: Literal["rule", "model", "threat_intelligence"]
    status: str = Field(max_length=40)
    reference: str | None = Field(default=None, max_length=2048)
    observed_at: datetime
    details: dict[str, JsonValue] = Field(default_factory=dict)


class Finding(ContractModel):
    id: UUID
    code: str = Field(max_length=100)
    description: str = Field(max_length=2000)
    severity: Literal["info", "caution", "high"]
    verification_status: Literal["documented_rule", "model_inference", "provider_report"]
    source_id: UUID
    observed_at: datetime
    attributes: dict[str, JsonValue] = Field(default_factory=dict)


class ModelResult(ContractModel):
    name: str
    version: str | None = None
    task: str
    status: Literal["available", "model_not_trained", "model_integrity_error", "model_incompatible", "invalid_manifest", "insufficient_features", "inference_error"]
    label: Literal["ham", "spam", "legitimate", "phishing"] | None = None
    decision_score: float | None = None
    score_type: Literal["uncalibrated_decision_function"] | None = None
    confidence: None = None
    observed_at: datetime
    source_id: UUID | None = None
    limitations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def consistent_prediction(self):
        if self.status == "available" and (self.label is None or self.version is None):
            raise ValueError("Available inference requires an actual label and model version")
        if self.status != "available" and (self.label is not None or self.decision_score is not None):
            raise ValueError("Unavailable inference cannot carry a prediction")
        if (self.decision_score is None) != (self.score_type is None):
            raise ValueError("A decision score requires its score type")
        return self


class Assessment(ContractModel):
    classification: Literal["SAFE_INDICATORS", "EXERCISE_CAUTION", "HIGH_RISK", "CONFIRMED_FRAUD"]
    risk_score: float | None = Field(default=None, ge=0, le=100)
    score_type: str | None = None
    explanation: str = Field(max_length=3000)
    methodology_version: str
    confidence: None = None
    missing_information: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def consistent_score(self):
        if (self.risk_score is None) != (self.score_type is None):
            raise ValueError("A risk score requires a defined methodology")
        return self


class InvestigationResponse(ContractModel):
    investigation_id: UUID
    status: Literal["completed", "partial"]
    subject: Subject
    assessment: Assessment
    findings: list[Finding]
    sources: list[EvidenceSource]
    models: list[ModelResult]
    limitations: list[str]
    recommended_actions: list[str]
    created_at: datetime
    expires_at: datetime

    @model_validator(mode="after")
    def findings_have_actual_sources(self):
        source_ids = {source.id for source in self.sources}
        if any(finding.source_id not in source_ids for finding in self.findings):
            raise ValueError("Finding references an absent source")
        if len(source_ids) != len(self.sources):
            raise ValueError("Duplicate evidence source identifiers")
        return self


class InvestigationList(ContractModel):
    items: list[InvestigationResponse]
    limit: int
    offset: int
    has_more: bool


class ErrorDetail(ContractModel):
    field: str
    message: str


class ErrorContent(ContractModel):
    code: str
    message: str
    details: list[ErrorDetail]
    request_id: UUID


class ErrorResponse(ContractModel):
    error: ErrorContent


ERROR_RESPONSES = {status: {"model": ErrorResponse} for status in (400, 401, 404, 408, 409, 413, 415, 422, 429, 500, 503)}
