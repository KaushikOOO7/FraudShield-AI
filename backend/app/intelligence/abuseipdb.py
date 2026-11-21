from datetime import datetime

from pydantic import BaseModel, Field, StrictBool, StrictInt, ValidationError

from backend.app.intelligence.base import ProviderFailure, ThreatProvider
from backend.app.utils.urls import parse_public_url


class IPReport(BaseModel):
    ipAddress: str
    isPublic: StrictBool
    abuseConfidenceScore: StrictInt = Field(ge=0, le=100)
    totalReports: StrictInt = Field(ge=0)
    lastReportedAt: datetime | None = None


class IPResponse(BaseModel):
    data: IPReport


class AbuseIPDB(ThreatProvider):
    default_cache_seconds = 300
    name = "abuseipdb"
    reference = "https://docs.abuseipdb.com/#check-endpoint"

    async def lookup(self, url):
        if not self.configured:
            return self.outcome("provider_not_configured")
        parsed = parse_public_url(url)
        if not parsed.ip_literal:
            return self.outcome("unsupported_input", limitations=["AbuseIPDB checks public IP literals only. No DNS resolution or domain-to-IP reputation inference was performed."])
        try:
            data = await self.fetch_json("GET", "https://api.abuseipdb.com/api/v2/check", headers={"Key": self._key}, params={"ipAddress": parsed.hostname, "maxAgeInDays": 30})
            report = IPResponse.model_validate(data).data
            if report.ipAddress != parsed.hostname or not report.isPublic:
                raise ProviderFailure("invalid_response")
            positive = report.totalReports > 0 and report.abuseConfidenceScore > 0
            return self.outcome("matched" if positive else "no_match", verdict="suspicious_indicators" if positive else "no_known_match", report_at=report.lastReportedAt, details={"scope": "ip_only", "provider_abuse_confidence_score": report.abuseConfidenceScore, "total_reports": report.totalReports}, limitations=["IP abuse reports and provider scores do not establish that a specific URL or caller is fraudulent; shared hosting may contain unrelated sites."])
        except ProviderFailure as exc:
            return self.failure_outcome(exc)
        except (ValidationError, ValueError, TypeError):
            return self.outcome("invalid_response")
