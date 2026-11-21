from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, StrictBool, StrictInt, model_validator

from backend.app.schemas.investigation import ContractModel, Finding


class InterpretationRequest(ContractModel):
    use_gemini: StrictBool = False


class EvidenceSelection(ContractModel):
    finding_ids: list[UUID] = Field(max_length=50)
    action_indices: list[Annotated[StrictInt, Field(ge=0)]] = Field(max_length=30)

    @model_validator(mode="after")
    def unique_references(self):
        if len(set(self.finding_ids)) != len(self.finding_ids) or len(set(self.action_indices)) != len(self.action_indices):
            raise ValueError("Duplicate selection references")
        return self


class InterpretationResponse(ContractModel):
    investigation_id: UUID
    status: Literal["provider_not_configured", "not_requested", "insufficient_evidence", "available", "provider_error", "invalid_response", "rate_limited"]
    provider: Literal["gemini"] = "gemini"
    model_used: str | None = None
    checked_at: datetime
    selected_findings: list[Finding] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    confidence: None = None
    limitations: list[str]

    @model_validator(mode="after")
    def no_unavailable_outputs(self):
        if self.status != "available" and (self.model_used is not None or self.selected_findings or self.recommended_actions):
            raise ValueError("Unavailable interpretation cannot carry generated outputs")
        return self
