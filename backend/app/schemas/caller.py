from pydantic import Field, field_validator

from backend.app.schemas.requests import SubmissionMetadata
from backend.app.utils.indicators import normalize_phone


class CallerRequest(SubmissionMetadata):
    phone_number: str = Field(min_length=8, max_length=32)

    @field_validator("phone_number")
    @classmethod
    def valid_phone(cls, value):
        return normalize_phone(value)
