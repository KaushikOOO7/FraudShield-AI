import base64
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field, StrictInt, ValidationError, field_validator

from backend.app.intelligence.base import ProviderFailure, ThreatProvider
from backend.app.utils.urls import parse_public_url


class URLAttributes(BaseModel):
    url: str
    last_analysis_date: StrictInt = Field(gt=0)
    last_analysis_stats: dict[str, StrictInt]

    @field_validator("last_analysis_stats")
    @classmethod
    def validate_counts(cls, counts):
        if not {"malicious", "suspicious", "harmless", "undetected"}.issubset(counts):
            raise ValueError("Incomplete detector counts")
        if any(value < 0 or value > 10000 for value in counts.values()):
            raise ValueError("Invalid detector count")
        if sum(counts.values()) == 0:
            raise ValueError("Report contains no detector results")
        return counts


class URLData(BaseModel):
    type: str
    id: str
    attributes: URLAttributes


class URLResponse(BaseModel):
    data: URLData


class VirusTotal(ThreatProvider):
    name = "virustotal"
    reference = "https://docs.virustotal.com/reference/url-info"

    async def lookup(self, url: str):
        if not self.configured:
            return self.outcome("provider_not_configured")
        # Lookup existing reports only. Never submit a new scan or install content.
        identifier = base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")
        try:
            body = await self.fetch_json(
                "GET", f"https://www.virustotal.com/api/v3/urls/{identifier}",
                headers={"x-apikey": self._key},
            )
            response = URLResponse.model_validate(body)
            attributes = response.data.attributes
            if response.data.type != "url" or parse_public_url(attributes.url).normalized != url:
                raise ProviderFailure("invalid_response")
            report_at = datetime.fromtimestamp(attributes.last_analysis_date, timezone.utc)
            now = datetime.now(timezone.utc)
            if report_at > now + timedelta(minutes=5):
                raise ProviderFailure("invalid_response")
            counts = attributes.last_analysis_stats
            verdict = "malicious_indicators" if counts["malicious"] else "suspicious_indicators" if counts["suspicious"] else "no_known_match"
            status = "matched" if verdict != "no_known_match" else "no_match"
            limitations = ["Detector votes are provider reports, not human-reviewed confirmation of fraud."]
            if report_at < now - timedelta(days=30):
                status = "stale"
                limitations.append("The last analysis is older than 30 days; current reputation is unverified.")
            if verdict == "no_known_match":
                limitations.append("A report with no malicious/suspicious votes is not a safety guarantee.")
            return self.outcome(status, verdict=verdict, report_at=report_at, detector_counts=counts, limitations=limitations, cache_ttl_seconds=300)
        except ProviderFailure as exc:
            return self.failure_outcome(exc)
        except (ValidationError, ValueError, TypeError, OverflowError, OSError):
            return self.outcome("invalid_response", limitations=["Provider response could not be validated."])
