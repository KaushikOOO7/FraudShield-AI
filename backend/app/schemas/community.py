from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, StrictBool, field_validator, model_validator
from pydantic_core import PydanticCustomError

from backend.app.schemas.investigation import ContractModel
from backend.app.utils.indicators import normalized_indicator
from backend.app.utils.privacy import has_sensitive_values

IndicatorType = Literal["url", "domain", "phone", "apk_sha256"]


class WatchlistRequest(ContractModel):
    indicator_type: IndicatorType
    value: str = Field(min_length=1, max_length=2048)

    @model_validator(mode="after")
    def valid_indicator(self):
        if has_sensitive_values(self.value):
            raise PydanticCustomError("sensitive_input", "Remove sensitive credentials")
        normalized_indicator(self.indicator_type, self.value)
        return self


class WatchlistResponse(ContractModel):
    id: UUID
    indicator_type: IndicatorType
    redacted_value: str
    created_at: datetime


class WatchlistList(ContractModel):
    items: list[WatchlistResponse]
    limit: int
    offset: int
    has_more: bool


class ReportRequest(ContractModel):
    subject_type: Literal["sms", "url", "domain", "phone", "apk_sha256"]
    subject: str = Field(min_length=1, max_length=5000)
    description: str = Field(min_length=1, max_length=5000)

    @field_validator("subject", "description")
    @classmethod
    def no_secrets(cls, value):
        if not value.strip() or any(ord(char) < 32 and char not in "\n\r\t" for char in value):
            raise ValueError("Text cannot be blank or contain controls")
        if has_sensitive_values(value):
            raise PydanticCustomError("sensitive_input", "Remove sensitive credentials")
        return value.strip()

    @model_validator(mode="after")
    def valid_subject(self):
        normalized_indicator(self.subject_type, self.subject)
        return self


class ReportResponse(ContractModel):
    id: UUID
    subject_type: str
    redacted_subject: str
    redacted_description: str
    moderation_status: Literal["unreviewed", "approved", "rejected"]
    verified_at: datetime | None
    created_at: datetime


class ReportList(ContractModel):
    items: list[ReportResponse]
    limit: int
    offset: int
    has_more: bool


class AlertPreferencesPatch(ContractModel):
    high_risk_alerts: StrictBool


class AlertPreferences(ContractModel):
    high_risk_alerts: StrictBool
    delivery: Literal["in_app_history"] = "in_app_history"


class AlertResponse(ContractModel):
    id: UUID
    investigation_id: UUID
    severity: Literal["info", "caution", "high"]
    message: str
    created_at: datetime
    read_at: datetime | None


class AlertList(ContractModel):
    items: list[AlertResponse]
    limit: int
    offset: int
    has_more: bool
