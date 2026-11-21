"""Opt-in registry RDAP lookup. No arbitrary WHOIS hosts or redirects are followed."""
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import quote

from pydantic import BaseModel, Field, ValidationError

from backend.app.intelligence.base import ProviderFailure, ThreatProvider
from backend.app.utils.urls import parse_public_url

# Fixed HTTPS origins verified against IANA's registry, 2026-11-21.
REGISTRIES = {
    "com": "https://rdap.verisign.com/com/v1/",
    "net": "https://rdap.verisign.com/net/v1/",
    "org": "https://rdap.publicinterestregistry.org/rdap/",
    "in": "https://rdap.nixiregistry.in/rdap/",
}


class Event(BaseModel):
    eventAction: str
    eventDate: datetime


class DomainRecord(BaseModel):
    objectClassName: Literal["domain"]
    ldhName: str
    events: list[Event] = Field(default_factory=list, max_length=100)


class RDAP(ThreatProvider):
    default_cache_seconds = 300
    name = "rdap"
    reference = "https://data.iana.org/rdap/dns.json"

    def __init__(self, enabled, client, timeout):
        super().__init__(None, client, timeout)
        self.enabled = enabled

    @property
    def configured(self):
        return self.enabled

    async def lookup(self, url):
        if not self.configured:
            return self.outcome("provider_not_configured")
        parsed = parse_public_url(url)
        labels = parsed.hostname.split(".")
        registry = REGISTRIES.get(labels[-1]) if not parsed.ip_literal else None
        if registry is None:
            return self.outcome("unsupported_input", limitations=["Only fixed com/net/org/in registry origins are supported; no arbitrary RDAP referral is followed."])
        # com/net/org registry registration names have two labels. For in,
        # query the exact hostname to avoid inventing public-suffix membership.
        subject = ".".join(labels[-2:]) if labels[-1] != "in" else parsed.hostname
        try:
            data = await self.fetch_json("GET", registry + "domain/" + quote(subject, safe=""))
            record = DomainRecord.model_validate(data)
            if record.ldhName.rstrip(".").casefold() != subject:
                raise ProviderFailure("invalid_response")
            registrations = [event.eventDate for event in record.events if event.eventAction == "registration"]
            now = datetime.now(timezone.utc)
            if any(value.tzinfo is None or value > now for value in registrations):
                raise ProviderFailure("invalid_response")
            created = min(registrations) if registrations else None
            return self.outcome("observed", details={"registration_name": subject, "registration_at": created.isoformat() if created else None, "registration_age_days": (now - created).days if created else None}, limitations=["Registry registration dates do not authenticate website ownership or establish fraud; no personal registrant data is retained.", "Subdomains and unlisted registry origins may have no supported record."])
        except ProviderFailure as exc:
            return self.failure_outcome(exc)
        except (ValidationError, ValueError, TypeError):
            return self.outcome("invalid_response")
