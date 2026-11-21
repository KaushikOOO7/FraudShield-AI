"""Synthetic HTTP contract fixtures ONLY. They are not real threat reports.

All transports are isolated HTTPX MockTransport. Nothing reaches live providers
or production databases. Shapes follow the official references in the adapters.
"""
import asyncio
import time
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr

from backend.app.core.config import Settings
from backend.app.intelligence.engine import IntelligenceEngine
from backend.app.intelligence.google_safe_browsing import GoogleSafeBrowsing
from backend.app.intelligence.virustotal import VirusTotal

FIXTURE_URL = "https://example.com/"


def lookup(provider_type, handler, key="isolated-test-key"):
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False) as client:
            provider = provider_type(SecretStr(key) if key else None, client, 0.5)
            return await provider.lookup(FIXTURE_URL)
    return asyncio.run(run())


@pytest.mark.parametrize("provider_type", [GoogleSafeBrowsing, VirusTotal])
def test_unconfigured_provider_does_not_make_a_request(provider_type):
    def never(request):
        raise AssertionError("No request is permitted without a configured key")
    result = lookup(provider_type, never, key=None)
    assert result.status == "provider_not_configured"
    assert result.verdict is None


def test_safe_browsing_empty_success_is_no_match_not_safe():
    result = lookup(GoogleSafeBrowsing, lambda request: httpx.Response(200, json={}))
    assert result.status == "no_match"
    assert result.verdict == "no_known_match"
    assert result.limitations


def test_safe_browsing_contract_match_is_attributed():
    def handler(request):
        assert request.url.host == "safebrowsing.googleapis.com"
        return httpx.Response(200, json={"matches": [{"threatType": "MALWARE", "platformType": "ANY_PLATFORM", "threatEntryType": "URL", "threat": {"url": FIXTURE_URL}, "cacheDuration": "300s"}]})
    result = lookup(GoogleSafeBrowsing, handler)
    assert result.status == "matched"
    assert result.threat_categories == ["MALWARE"]


@pytest.mark.parametrize("payload", [{"unexpected": []}, {"matches": [{}]}, {"matches": [{"threatType": "MALWARE"}]}])
def test_malformed_response_does_not_become_no_match(payload):
    result = lookup(GoogleSafeBrowsing, lambda request: httpx.Response(200, json=payload))
    assert result.status == "invalid_response"
    assert result.verdict is None


@pytest.mark.parametrize("status", [401, 403, 404, 429, 500, 302])
def test_failure_and_rate_limit_are_not_clean_results(status):
    result = lookup(GoogleSafeBrowsing, lambda request: httpx.Response(status, json={}, headers={"Retry-After": "30", "Location": "http://127.0.0.1/"}))
    assert result.verdict is None
    if status == 429:
        assert result.status == "rate_limited"
        assert result.retry_after_seconds == 30


def test_retry_is_bounded():
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(503, json={})
    assert lookup(GoogleSafeBrowsing, handler).status == "provider_error"
    assert len(calls) == 2


def test_timeout_returns_provider_error():
    def handler(request):
        raise httpx.ReadTimeout("isolated timeout fixture")
    assert lookup(VirusTotal, handler).verdict is None


def vt_fixture(malicious=0, suspicious=0, age_seconds=0):
    return {"data": {"type": "url", "id": "isolated-nonproduction-response-id", "attributes": {
        "url": FIXTURE_URL, "last_analysis_date": int(time.time()) - age_seconds,
        "last_analysis_stats": {"malicious": malicious, "suspicious": suspicious, "harmless": 10, "undetected": 5},
    }}}


def test_virustotal_actual_contract_fields_not_random_scores():
    result = lookup(VirusTotal, lambda request: httpx.Response(200, json=vt_fixture(malicious=3)))
    assert result.detector_counts["malicious"] == 3
    assert result.verdict == "malicious_indicators"
    assert result.report_at is not None


def test_stale_report_is_explicit():
    result = lookup(VirusTotal, lambda request: httpx.Response(200, json=vt_fixture(age_seconds=31 * 86400)))
    assert result.status == "stale"


def test_no_engine_results_is_not_a_clean_report():
    payload = vt_fixture()
    payload["data"]["attributes"]["last_analysis_stats"] = {}
    result = lookup(VirusTotal, lambda request: httpx.Response(200, json=payload))
    assert result.status == "invalid_response"


def test_cache_preserves_timestamp_and_explicit_consent():
    async def run():
        calls = []
        def handler(request):
            calls.append(request)
            return httpx.Response(200, json={"matches": [{"threatType": "MALWARE", "platformType": "ANY_PLATFORM", "threatEntryType": "URL", "threat": {"url": FIXTURE_URL}, "cacheDuration": "300s"}]})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            settings = Settings(google_safe_browsing_api_key="isolated-test-key", _env_file=None)
            engine = IntelligenceEngine(settings, client)
            owner = uuid4()
            unrequested = await engine.lookup_url(FIXTURE_URL, owner, requested=False)
            assert unrequested[0].status == "not_requested"
            assert calls == []
            first = (await engine.lookup_url(FIXTURE_URL, owner, requested=True))[0]
            second = (await engine.lookup_url(FIXTURE_URL, owner, requested=True))[0]
            assert len(calls) == 1
            assert second.cached
            assert first.checked_at == second.checked_at
            await engine.lookup_url(FIXTURE_URL, uuid4(), requested=True)
            assert len(calls) == 2
    asyncio.run(run())


def test_safe_browsing_cache_cannot_exceed_provider_validity():
    payload = {"matches": [{"threatType": "MALWARE", "platformType": "ANY_PLATFORM", "threatEntryType": "URL", "threat": {"url": FIXTURE_URL}, "cacheDuration": "30s"}]}
    outcome = lookup(GoogleSafeBrowsing, lambda request: httpx.Response(200, json=payload))
    assert outcome.cache_ttl_seconds == 30
    assert outcome.valid_until is not None
    payload["matches"][0]["cacheDuration"] = "0s"
    expired = lookup(GoogleSafeBrowsing, lambda request: httpx.Response(200, json=payload))
    assert expired.status == "stale"
    assert expired.cache_ttl_seconds == 0
