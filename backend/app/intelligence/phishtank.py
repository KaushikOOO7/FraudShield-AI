from datetime import datetime, timezone

from pydantic import BaseModel, StrictBool, ValidationError, field_validator

from backend.app.intelligence.base import ProviderFailure, ThreatProvider
from backend.app.utils.urls import parse_public_url


class PhishTankResult(BaseModel):
    url: str
    in_database: StrictBool
    verified: StrictBool | None = None
    valid: StrictBool | None = None
    verified_at: datetime | None = None

    @field_validator("verified", "valid", mode="before")
    @classmethod
    def documented_flags(cls, value):
        # The official PHP/JSON contract uses y/n as well as JSON booleans.
        return {"y": True, "n": False}.get(value, value) if isinstance(value, str) else value


class PhishTankResponse(BaseModel):
    results: PhishTankResult


class PhishTank(ThreatProvider):
    default_cache_seconds = 300
    name = "phishtank"
    reference = "https://www.phishtank.org/api_info.php"

    async def lookup(self, url):
        if not self.configured:
            return self.outcome("provider_not_configured")
        try:
            data = await self.fetch_json("POST", "https://checkurl.phishtank.com/checkurl/", headers={"User-Agent": "phishtank/FraudShieldAI"}, data={"url": url, "format": "json", "app_key": self._key})
            report = PhishTankResponse.model_validate(data).results
            if parse_public_url(report.url).normalized != url:
                raise ProviderFailure("invalid_response")
            if not report.in_database:
                if report.verified is True or report.valid is True:
                    raise ProviderFailure("invalid_response")
                return self.outcome("no_match", verdict="no_known_match", limitations=["No PhishTank entry does not guarantee destination safety."])
            if report.verified is None or report.valid is None:
                raise ProviderFailure("invalid_response")
            if report.verified and report.valid:
                if report.verified_at is None or report.verified_at.tzinfo is None or report.verified_at > datetime.now(timezone.utc):
                    raise ProviderFailure("invalid_response")
                return self.outcome("matched", verdict="malicious_indicators", report_at=report.verified_at, threat_categories=["community_verified_phishing"], limitations=["A PhishTank community-verified listing is not human-reviewed confirmation of financial fraud by this platform."])
            return self.outcome("observed", details={"in_database": True, "verified": report.verified, "valid": report.valid}, limitations=["A record exists but is not a verified valid phishing listing; no reputation verdict was substituted."])
        except ProviderFailure as exc:
            return self.failure_outcome(exc)
        except (ValidationError, ValueError, TypeError):
            return self.outcome("invalid_response")
