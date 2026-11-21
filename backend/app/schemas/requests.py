from typing import Literal
from uuid import UUID

from pydantic import Field, StrictBool, field_validator
from pydantic_core import PydanticCustomError

from backend.app.schemas.investigation import ContractModel
from backend.app.utils.privacy import has_sensitive_values
from backend.app.utils.urls import parse_public_url


class SubmissionMetadata(ContractModel):
    source: Literal["android_share", "android_manual", "web_share", "web_manual", "api"] = "api"
    device_id: UUID | None = None
    use_threat_intelligence: StrictBool = Field(default=False, description="Explicit opt-in to forward extracted URLs to configured third-party providers")


class SMSRequest(SubmissionMetadata):
    content: str = Field(min_length=1, max_length=5000)

    @field_validator("content")
    @classmethod
    def valid_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message cannot be blank")
        if any(ord(character) < 32 and character not in "\n\r\t" for character in value) or "\x7f" in value:
            raise ValueError("Unsupported control characters")
        if has_sensitive_values(value):
            raise PydanticCustomError("sensitive_input", "Sensitive credentials must be redacted")
        return value.strip()


class URLRequest(SubmissionMetadata):
    url: str = Field(min_length=1, max_length=2048)

    @field_validator("url")
    @classmethod
    def valid_url(cls, value: str) -> str:
        if has_sensitive_values(value):
            raise PydanticCustomError("sensitive_input", "Sensitive credentials must be redacted")
        return parse_public_url(value).normalized
