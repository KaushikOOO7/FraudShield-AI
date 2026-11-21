from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import parse_qs, urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore", hide_input_in_errors=True
    )

    app_env: Literal["development", "test", "production"] = "development"
    database_url: SecretStr = SecretStr(
        f"sqlite:///{PROJECT_ROOT / 'data' / 'fraudshield.sqlite3'}"
    )
    supabase_url: str | None = None
    supabase_jwt_secret: SecretStr | None = None
    jwt_audience: str = "authenticated"
    sms_model_dir: Path = PROJECT_ROOT / "backend/app/ml/models"
    url_model_dir: Path = PROJECT_ROOT / "backend/app/ml/models"
    google_safe_browsing_api_key: SecretStr | None = None
    virustotal_api_key: SecretStr | None = None
    urlhaus_api_key: SecretStr | None = None
    phishtank_api_key: SecretStr | None = None
    abuseipdb_api_key: SecretStr | None = None
    enable_rdap: bool = False
    enable_crtsh: bool = False
    gemini_api_key: SecretStr | None = None
    gemini_model: str | None = Field(default=None, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
    cors_origins: list[str] = Field(default_factory=list)
    allowed_hosts: list[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "testserver"]
    )
    max_request_bytes: int = Field(default=32768, ge=1024, le=1048576)
    request_body_timeout_seconds: float = Field(default=15, gt=0, le=60)
    rate_limit_per_minute: int = Field(default=30, ge=1, le=1000)
    ip_rate_limit_per_minute: int = Field(default=120, ge=1, le=10000)
    provider_timeout_seconds: float = Field(default=5, gt=0, le=15)
    jwks_cache_seconds: int = Field(default=300, ge=30, le=600)
    investigation_retention_days: int = Field(default=30, ge=1, le=365)
    audit_retention_days: int = Field(default=180, ge=1, le=365)
    community_report_retention_days: int = Field(default=30, ge=1, le=365)
    qr_max_upload_bytes: int = Field(default=2097152, ge=1024, le=5242880)
    apk_max_upload_bytes: int = Field(default=20971520, ge=1024, le=52428800)

    @field_validator("supabase_url", mode="before")
    @classmethod
    def validate_supabase_url(cls, value: str | None) -> str | None:
        if not value:
            return None
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.path not in ("", "/")
        ):
            raise ValueError("SUPABASE_URL must be a HTTPS project origin")
        return value.rstrip("/")

    @field_validator("supabase_jwt_secret", "google_safe_browsing_api_key", "virustotal_api_key", "urlhaus_api_key", "phishtank_api_key", "abuseipdb_api_key", "gemini_api_key", mode="before")
    @classmethod
    def empty_secret_is_unconfigured(cls, value: str | SecretStr | None):
        return None if value == "" else value

    @field_validator("gemini_model", mode="before")
    @classmethod
    def empty_model_is_unconfigured(cls, value):
        return None if value == "" else value

    @model_validator(mode="after")
    def validate_deployment(self):
        database = self.database_url.get_secret_value()
        if not database.startswith(("sqlite:///", "postgresql+psycopg://")):
            raise ValueError("DATABASE_URL must use sqlite:/// or postgresql+psycopg://")
        if self.supabase_jwt_secret and len(self.supabase_jwt_secret.get_secret_value()) < 32:
            raise ValueError("Legacy JWT verification secret must contain at least 32 characters")
        if "*" in self.cors_origins:
            raise ValueError("CORS origins must be explicit")
        if self.app_env == "production":
            if not database.startswith("postgresql+psycopg://"):
                raise ValueError("Production requires PostgreSQL")
            if not self.supabase_url:
                raise ValueError("Production requires Supabase Auth configuration")
            if parse_qs(urlsplit(database).query).get("sslmode") != ["verify-full"]:
                raise ValueError("Production PostgreSQL requires sslmode=verify-full")
            if not self.allowed_hosts or "*" in self.allowed_hosts or "testserver" in self.allowed_hosts:
                raise ValueError("Production requires explicit deployed host names")
        return self

    @property
    def jwt_issuer(self) -> str | None:
        return f"{self.supabase_url}/auth/v1" if self.supabase_url else None


@lru_cache
def get_settings() -> Settings:
    return Settings()
