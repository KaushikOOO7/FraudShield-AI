from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from backend.app.schemas.investigation import ContractModel


class ExportedComponent(ContractModel):
    type: Literal["activity", "activity-alias", "service", "receiver", "provider"]
    name: str | None = Field(max_length=1000)


class CertificateMetadata(ContractModel):
    sha256: str = Field(pattern="^[0-9a-f]{64}$")
    subject: str = Field(max_length=500)
    issuer: str = Field(max_length=500)
    not_before: datetime
    not_after: datetime


class APKMetadata(ContractModel):
    parser: Literal["androguard"]
    parser_version: str = Field(max_length=64)
    package_name: str = Field(min_length=1, max_length=255)
    application_name: str | None = Field(max_length=2048)
    version_name: str | None = Field(max_length=255)
    version_code: str | None = Field(max_length=64)
    requested_permissions: list[str] = Field(max_length=1000)
    explicitly_exported_components: list[ExportedComponent] = Field(max_length=1000)
    certificates: list[CertificateMetadata] = Field(max_length=50)
    certificate_status: Literal["parsed", "unavailable"]
    embedded_url_candidates: list[str] = Field(max_length=20)


class APKWorkerResult(ContractModel):
    status: Literal["parsed", "parser_unavailable", "invalid_apk"]
    metadata: APKMetadata | None

    @model_validator(mode="after")
    def consistent_metadata(self):
        if (self.status == "parsed") != (self.metadata is not None):
            raise ValueError("Parsed APK results require actual structured metadata")
        return self
