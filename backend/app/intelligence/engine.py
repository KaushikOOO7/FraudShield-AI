import asyncio
import hashlib
import time
from collections import OrderedDict
from uuid import UUID

from backend.app.intelligence.google_safe_browsing import GoogleSafeBrowsing
from backend.app.intelligence.virustotal import VirusTotal
from backend.app.intelligence.urlhaus import URLhaus
from backend.app.intelligence.phishtank import PhishTank
from backend.app.intelligence.abuseipdb import AbuseIPDB
from backend.app.intelligence.whois_lookup import RDAP
from backend.app.intelligence.crtsh import CrtSH


class IntelligenceEngine:
    def __init__(self, settings, client):
        self.providers = [
            GoogleSafeBrowsing(settings.google_safe_browsing_api_key, client, settings.provider_timeout_seconds),
            VirusTotal(settings.virustotal_api_key, client, settings.provider_timeout_seconds),
            URLhaus(settings.urlhaus_api_key, client, settings.provider_timeout_seconds),
            PhishTank(settings.phishtank_api_key, client, settings.provider_timeout_seconds),
            AbuseIPDB(settings.abuseipdb_api_key, client, settings.provider_timeout_seconds),
            RDAP(settings.enable_rdap, client, settings.provider_timeout_seconds),
            CrtSH(settings.enable_crtsh, client, settings.provider_timeout_seconds),
        ]
        self._cache = OrderedDict()
        self._last_results = {}

    async def lookup_url(self, url: str, owner_id: UUID, requested: bool):
        async def query(provider):
            if not provider.configured:
                return provider.outcome("provider_not_configured")
            if not requested:
                return provider.outcome("not_requested")
            cache_key = hashlib.sha256(f"{owner_id}|{provider.name}|{url}".encode()).hexdigest()
            stored = self._cache.pop(cache_key, None)
            if stored and stored[0] > time.monotonic():
                self._cache[cache_key] = stored
                return stored[1].model_copy(update={"cached": True}, deep=True)
            outcome = await provider.lookup(url)
            self._last_results[provider.name] = outcome
            ttl = min(outcome.cache_ttl_seconds, 300)
            if outcome.status in ("matched", "no_match", "stale", "observed") and ttl > 0:
                self._cache[cache_key] = (time.monotonic() + ttl, outcome)
                if len(self._cache) > 256:
                    self._cache.popitem(last=False)
            return outcome

        return await asyncio.gather(*(query(provider) for provider in self.providers))

    def system_status(self):
        statuses = []
        for provider in self.providers:
            last = self._last_results.get(provider.name)
            statuses.append({
                "name": provider.name,
                "status": last.status if last else "configured_not_verified" if provider.configured else "provider_not_configured",
                "last_checked_at": last.checked_at.isoformat() if last else None,
                "reference": provider.reference,
            })
        return statuses
