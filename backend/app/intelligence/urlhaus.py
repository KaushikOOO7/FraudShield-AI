from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ValidationError

from backend.app.intelligence.base import ProviderFailure, ThreatProvider
from backend.app.utils.urls import parse_public_url


class URLhausReport(BaseModel):
    query_status: Literal["ok", "no_results"]
    url: str | None = None
    url_status: Literal["online", "offline"] | None = None
    threat: str | None = None
    date_added: datetime | None = None


class URLhaus(ThreatProvider):
    default_cache_seconds = 300
    name = "urlhaus"
    reference = "https://urlhaus.abuse.ch/api/"

    async def lookup(self, url):
        if not self.configured:
            return self.outcome("provider_not_configured")
        try:
            data = await self.fetch_json("POST", "https://urlhaus-api.abuse.ch/v1/url/", headers={"Auth-Key": self._key}, data={"url": url})
            report = URLhausReport.model_validate(data)
            if report.query_status == "no_results":
                if any(value is not None for value in (report.url_status, report.threat, report.date_added)):
                    raise ProviderFailure("invalid_response")
                return self.outcome("no_match", verdict="no_known_match", limitations=["No URLhaus malware-distribution record is not proof of safety or absence of phishing."])
            if report.url is None or parse_public_url(report.url).normalized != url or report.url_status is None or report.threat != "malware_download" or report.date_added is None:
                raise ProviderFailure("invalid_response")
            observed = report.date_added.replace(tzinfo=timezone.utc) if report.date_added.tzinfo is None else report.date_added
            if observed > datetime.now(timezone.utc):
                raise ProviderFailure("invalid_response")
            return self.outcome("matched" if report.url_status == "online" else "stale", verdict="malicious_indicators", report_at=observed, threat_categories=["malware_download"], details={"reported_url_status": report.url_status}, limitations=["URLhaus lists reported malware-distribution URLs; the destination was not independently fetched or human-reviewed here."])
        except ProviderFailure as exc:
            return self.failure_outcome(exc)
        except (ValidationError, ValueError, TypeError):
            return self.outcome("invalid_response")
