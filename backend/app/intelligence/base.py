import asyncio
import json
from datetime import datetime, timezone
from typing import Literal

import httpx
from pydantic import Field, JsonValue, model_validator

from backend.app.schemas.investigation import ContractModel


class ProviderOutcome(ContractModel):
    provider: str
    status: Literal["provider_not_configured", "not_requested", "matched", "no_match", "not_found", "stale", "observed", "unsupported_input", "invalid_response", "provider_error", "rate_limited"]
    verdict: Literal["malicious_indicators", "suspicious_indicators", "no_known_match"] | None = None
    checked_at: datetime
    report_at: datetime | None = None
    threat_categories: list[str] = Field(default_factory=list)
    detector_counts: dict[str, int] = Field(default_factory=dict)
    retry_after_seconds: int | None = None
    cached: bool = False
    cache_ttl_seconds: int = Field(default=0, ge=0, le=86400)
    valid_until: datetime | None = None
    limitations: list[str] = Field(default_factory=list)
    details: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def unavailable_is_not_clean(self):
        if self.status not in ("matched", "no_match", "stale") and self.verdict is not None:
            raise ValueError("Unavailable providers cannot carry threat verdicts")
        if self.status == "no_match" and self.verdict != "no_known_match":
            raise ValueError("No-match status must be explicit")
        return self


class ProviderFailure(Exception):
    def __init__(self, status: str, retry_after: int | None = None):
        self.status = status
        self.retry_after = retry_after
        super().__init__(status)


class ThreatProvider:
    name: str
    reference: str
    default_cache_seconds: int = 0

    def __init__(self, key, client: httpx.AsyncClient, timeout: float):
        self._key = key.get_secret_value() if key else None
        self.client = client
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self._key)

    def outcome(self, status: str, **kwargs) -> ProviderOutcome:
        if status in ("matched", "no_match", "stale", "observed"):
            kwargs.setdefault("cache_ttl_seconds", self.default_cache_seconds)
        return ProviderOutcome(provider=self.name, status=status, checked_at=datetime.now(timezone.utc), **kwargs)

    def failure_outcome(self, exc: ProviderFailure) -> ProviderOutcome:
        return self.outcome(exc.status, retry_after_seconds=exc.retry_after, limitations=["No validated threat verdict was obtained from this provider."])

    async def fetch_json(self, method: str, endpoint: str, **kwargs) -> dict:
        list_response = kwargs.pop("list_response", False)
        headers = {"Accept-Encoding": "identity", **kwargs.pop("headers", {})}
        for attempt in range(2):
            try:
                async with asyncio.timeout(self.timeout):
                    async with self.client.stream(method, endpoint, headers=headers, follow_redirects=False, **kwargs) as response:
                        if response.status_code in (429, 509):
                            raw_retry = response.headers.get("retry-after", "")
                            retry = int(raw_retry) if raw_retry.isdigit() else None
                            raise ProviderFailure("rate_limited", retry)
                        if response.status_code == 404:
                            raise ProviderFailure("not_found")
                        if response.status_code >= 500:
                            if attempt == 0:
                                continue
                            raise ProviderFailure("provider_error")
                        if response.status_code != 200:
                            raise ProviderFailure("provider_error")
                        if response.headers.get("content-type", "").lower().split(";", 1)[0].strip() not in ("application/json", "application/rdap+json"):
                            raise ProviderFailure("invalid_response")
                        if response.headers.get("content-encoding", "identity").lower() != "identity":
                            raise ProviderFailure("invalid_response")
                        content = bytearray()
                        async for chunk in response.aiter_bytes():
                            content.extend(chunk)
                            if len(content) > 262144:
                                raise ProviderFailure("invalid_response")
                    data = json.loads(content)
                    if list_response:
                        if not isinstance(data, list):
                            raise ProviderFailure("invalid_response")
                        return {"items": data}
                    if not isinstance(data, dict):
                        raise ProviderFailure("invalid_response")
                    return data
            except ProviderFailure:
                raise
            except (json.JSONDecodeError, UnicodeDecodeError):
                raise ProviderFailure("invalid_response") from None
            except (httpx.HTTPError, TimeoutError):
                if attempt == 1:
                    raise ProviderFailure("provider_error") from None
                await asyncio.sleep(0.1)
        raise ProviderFailure("provider_error")
