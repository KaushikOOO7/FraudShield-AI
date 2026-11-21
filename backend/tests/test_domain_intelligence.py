"""Isolated RDAP/CT contract fixtures, not real registration/certificate data."""
import asyncio

import httpx
import pytest

from backend.app.intelligence.crtsh import CrtSH
from backend.app.intelligence.whois_lookup import RDAP


def query(kind, payload, enabled=True, url="https://example.com/", content_type="application/json"):
    async def run():
        calls = []
        def handler(request):
            calls.append(request)
            return httpx.Response(200, json=payload, headers={"Content-Type": content_type})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await kind(enabled, client, 0.5).lookup(url)
        return result, calls
    return asyncio.run(run())


@pytest.mark.parametrize("kind", [RDAP, CrtSH])
def test_public_provider_requires_explicit_enable(kind):
    result, calls = query(kind, {}, enabled=False)
    assert result.status == "provider_not_configured" and calls == []


def test_rdap_registry_attribution_and_no_personal_contacts():
    payload = {"objectClassName": "domain", "ldhName": "EXAMPLE.COM", "events": [{"eventAction": "registration", "eventDate": "2024-01-01T00:00:00Z"}], "entities": [{"private": "ISOLATED-PERSONAL-FIXTURE"}]}
    result, calls = query(RDAP, payload, url="https://www.example.com/", content_type="application/rdap+json")
    assert result.status == "observed" and result.verdict is None
    assert result.details["registration_at"] == "2024-01-01T00:00:00+00:00"
    assert calls[0].url.host == "rdap.verisign.com" and calls[0].url.path.endswith("/domain/example.com")
    assert "ISOLATED-PERSONAL" not in str(result)
    payload["ldhName"] = "other.com"
    assert query(RDAP, payload)[0].status == "invalid_response"


def test_rdap_indian_registry_and_unsupported_origins():
    result, calls = query(RDAP, {"objectClassName": "domain", "ldhName": "example.in"}, url="https://example.in/")
    assert result.status == "observed"
    assert result.details["registration_at"] is None
    assert calls[0].url.host == "rdap.nixiregistry.in"
    result, calls = query(RDAP, {}, url="https://example.xyz/")
    assert result.status == "unsupported_input" and calls == []


def test_ct_returns_observations_not_legitimacy_or_clean_verdict():
    payload = [{"id": 1, "name_value": "example.com", "entry_timestamp": "2024-01-01T00:00:00"}, {"id": 2, "name_value": "other.com", "entry_timestamp": "2024-01-02T00:00:00"}]
    result, calls = query(CrtSH, payload)
    assert result.status == "observed" and result.verdict is None
    assert result.details["matching_certificate_records"] == 1
    assert calls[0].url.host == "crt.sh"
    empty, _ = query(CrtSH, [])
    assert empty.status == "observed" and empty.details["matching_certificate_records"] == 0


@pytest.mark.parametrize("kind", [RDAP, CrtSH])
def test_invalid_domain_provider_response_is_not_clean(kind):
    result, _ = query(kind, {"unexpected": "ISOLATED-FIXTURE"})
    assert result.status == "invalid_response" and result.verdict is None
