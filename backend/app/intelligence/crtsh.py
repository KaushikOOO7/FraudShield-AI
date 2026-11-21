from datetime import datetime, timezone

from pydantic import BaseModel, Field, StrictInt, ValidationError

from backend.app.intelligence.base import ProviderFailure, ThreatProvider
from backend.app.utils.urls import parse_public_url


class CertificateEntry(BaseModel):
    id: StrictInt
    name_value: str = Field(max_length=10000)
    entry_timestamp: datetime


class CTResponse(BaseModel):
    items: list[CertificateEntry] = Field(max_length=2000)


class CrtSH(ThreatProvider):
    default_cache_seconds = 300
    name = "crtsh"
    reference = "https://crt.sh/"

    def __init__(self, enabled, client, timeout):
        super().__init__(None, client, timeout)
        self.enabled = enabled

    @property
    def configured(self):
        return self.enabled

    async def lookup(self, url):
        if not self.configured:
            return self.outcome("provider_not_configured")
        hostname = parse_public_url(url).hostname
        try:
            data = await self.fetch_json("GET", "https://crt.sh/", params={"q": hostname, "output": "json"}, list_response=True)
            report = CTResponse.model_validate(data)
            records = {}
            for item in report.items:
                names = item.name_value.casefold().splitlines()
                if hostname in names or any(name.startswith("*.") and hostname.endswith(name[1:]) and hostname.count(".") == name.count(".") for name in names):
                    records[item.id] = item
            times = [item.entry_timestamp.replace(tzinfo=timezone.utc) if item.entry_timestamp.tzinfo is None else item.entry_timestamp for item in records.values()]
            if any(value > datetime.now(timezone.utc) for value in times):
                raise ProviderFailure("invalid_response")
            return self.outcome("observed", details={"matching_certificate_records": len(records), "latest_log_entry_at": max(times).isoformat() if times else None}, limitations=["Certificate-transparency observations do not verify a live TLS connection, ownership, certificate validity or destination safety."])
        except ProviderFailure as exc:
            return self.failure_outcome(exc)
        except (ValidationError, ValueError, TypeError):
            return self.outcome("invalid_response")
