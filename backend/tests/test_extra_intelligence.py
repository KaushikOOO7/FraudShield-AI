"""Explicit non-production provider contract fixtures. No live report claims."""
import asyncio
from datetime import datetime, timezone

import httpx
import pytest
from pydantic import SecretStr

from backend.app.intelligence.abuseipdb import AbuseIPDB
from backend.app.intelligence.phishtank import PhishTank
from backend.app.intelligence.urlhaus import URLhaus


def query(kind, payload, url="https://example.com/", key="isolated-key", status=200):
    async def run():
        calls = []
        def handler(request):
            calls.append(request)
            return httpx.Response(status, json=payload)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await kind(SecretStr(key) if key else None, client, 0.5).lookup(url)
        return result, calls
    return asyncio.run(run())


@pytest.mark.parametrize("kind", [URLhaus, PhishTank, AbuseIPDB])
def test_optional_keys_never_create_requests_or_clean_verdicts(kind):
    result, calls = query(kind, {}, key=None)
    assert result.status == "provider_not_configured" and result.verdict is None and calls == []


def test_urlhaus_report_validation_and_offline_staleness():
    report = {"query_status": "ok", "url": "https://example.com/", "url_status": "online", "threat": "malware_download", "date_added": "2024-01-01 00:00:00"}
    result, calls = query(URLhaus, report)
    assert result.status == "matched" and result.verdict == "malicious_indicators"
    assert calls[0].url.host == "urlhaus-api.abuse.ch" and calls[0].headers["Auth-Key"] == "isolated-key"
    report["url_status"] = "offline"
    assert query(URLhaus, report)[0].status == "stale"
    report["url"] = "https://example.org/"
    assert query(URLhaus, report)[0].status == "invalid_response"
    assert query(URLhaus, {"query_status": "no_results"})[0].verdict == "no_known_match"


def test_phishtank_documented_flags_verified_and_unreviewed():
    report = {"results": {"url": "https://example.com/", "in_database": True, "verified": "y", "valid": "y", "verified_at": "2024-01-01T00:00:00Z"}}
    result, calls = query(PhishTank, report)
    assert result.status == "matched"
    assert calls[0].url.host == "checkurl.phishtank.com"
    assert calls[0].headers["User-Agent"] == "phishtank/FraudShieldAI"
    report["results"]["verified"] = "n"
    result, _ = query(PhishTank, report)
    assert result.status == "observed" and result.verdict is None
    assert query(PhishTank, {}, status=509)[0].status == "rate_limited"


def test_abuseipdb_is_ip_scoped_not_domain_reputation():
    result, calls = query(AbuseIPDB, {})
    assert result.status == "unsupported_input" and calls == []
    payload = {"data": {"ipAddress": "8.8.8.8", "isPublic": True, "abuseConfidenceScore": 20, "totalReports": 2, "lastReportedAt": "2024-01-01T00:00:00Z"}}
    result, calls = query(AbuseIPDB, payload, url="https://8.8.8.8/")
    assert result.verdict == "suspicious_indicators"
    assert result.details["scope"] == "ip_only"
    assert calls[0].headers["Key"] == "isolated-key"
    payload["data"]["abuseConfidenceScore"] = "20"
    assert query(AbuseIPDB, payload, url="https://8.8.8.8/")[0].status == "invalid_response"


@pytest.mark.parametrize("kind", [URLhaus, PhishTank, AbuseIPDB])
def test_malformed_reports_not_interpreted_as_safe(kind):
    result, _ = query(kind, {"unexpected": "ISOLATED RESPONSE"}, url="https://8.8.8.8/" if kind == AbuseIPDB else "https://example.com/")
    assert result.status == "invalid_response" and result.verdict is None


@pytest.mark.parametrize("kind,payload", [
    (URLhaus, {"query_status": "no_results", "url_status": "online", "threat": "malware_download"}),
    (PhishTank, {"results": {"url": "https://example.com/", "in_database": False, "verified": True, "valid": True}}),
])
def test_contradictory_no_match_reports_have_no_clean_verdict(kind, payload):
    result, _ = query(kind, payload)
    assert result.status == "invalid_response"
    assert result.verdict is None
