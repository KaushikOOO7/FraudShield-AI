from typing import Literal
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.app.intelligence.base import ProviderFailure, ThreatProvider
from backend.app.utils.urls import parse_public_url


class ThreatEntry(BaseModel):
    url: str


class ThreatMatch(BaseModel):
    threatType: Literal["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"]
    platformType: str
    threatEntryType: Literal["URL"]
    threat: ThreatEntry
    cacheDuration: str = Field(pattern=r"^\d+(?:\.\d+)?s$", max_length=32)


class MatchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    matches: list[ThreatMatch] = Field(default_factory=list, max_length=100)


class GoogleSafeBrowsing(ThreatProvider):
    name = "google_safe_browsing"
    reference = "https://developers.google.com/safe-browsing/v4/reference/rest/v4/threatMatches/find"
    advisory = "https://developers.google.com/safe-browsing/v4/advisory"

    async def lookup(self, url: str):
        if not self.configured:
            return self.outcome("provider_not_configured")
        try:
            body = await self.fetch_json(
                "POST", "https://safebrowsing.googleapis.com/v4/threatMatches:find",
                params={"key": self._key},
                json={
                    "client": {"clientId": "fraudshield-ai", "clientVersion": "0.1.0"},
                    "threatInfo": {
                        "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
                        "platformTypes": ["ANY_PLATFORM"], "threatEntryTypes": ["URL"],
                        "threatEntries": [{"url": url}],
                    },
                },
            )
            response = MatchResponse.model_validate(body)
            if any(parse_public_url(match.threat.url).normalized != url for match in response.matches):
                raise ProviderFailure("invalid_response")
            if response.matches:
                ttl = min(86400, int(min(float(match.cacheDuration[:-1]) for match in response.matches)))
                return self.outcome(
                    "matched" if ttl > 0 else "stale", verdict="malicious_indicators",
                    threat_categories=sorted({match.threatType for match in response.matches}),
                    cache_ttl_seconds=ttl, valid_until=datetime.now(timezone.utc) + timedelta(seconds=ttl),
                    limitations=["Google reports potential risk; false positives and false negatives remain possible. Advisory provided by Google."],
                )
            return self.outcome("no_match", verdict="no_known_match", limitations=["No match in checked Safe Browsing lists is not a safety guarantee."])
        except ProviderFailure as exc:
            return self.failure_outcome(exc)
        except (ValidationError, ValueError, TypeError):
            return self.outcome("invalid_response", limitations=["Provider response could not be validated."])
