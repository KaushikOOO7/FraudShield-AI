"""End-to-end isolated provider HTTP fixtures. Never presented as live intelligence."""
import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database.models import ThreatIntelligenceResult


def test_configured_adapters_aggregate_real_validated_contracts_and_storage(api_factory, token_factory):
    def handler(request):
        if request.url.host == "urlhaus-api.abuse.ch":
            return httpx.Response(200, json={"query_status": "ok", "url": "https://example.com/", "url_status": "online", "threat": "malware_download", "date_added": "2024-01-01 00:00:00"})
        if request.url.host == "checkurl.phishtank.com":
            return httpx.Response(200, json={"results": {"url": "https://example.com/", "in_database": True, "verified": "y", "valid": "y", "verified_at": "2024-01-01T00:00:00Z"}})
        if request.url.host == "rdap.verisign.com":
            return httpx.Response(200, json={"objectClassName": "domain", "ldhName": "example.com", "events": []})
        if request.url.host == "crt.sh":
            return httpx.Response(200, json=[])
        raise AssertionError("Unexpected provider destination")
    client, app, calls = api_factory(provider_handler=handler, urlhaus_api_key="isolated-key", phishtank_api_key="isolated-key", abuseipdb_api_key="isolated-key", enable_rdap=True, enable_crtsh=True)
    auth = {"Authorization": f"Bearer {token_factory()}"}
    submission = {"url": "https://example.com/", "use_threat_intelligence": True}
    first = client.post("/api/v1/analyze/url", headers=auth, json=submission)
    assert first.status_code == 201, first.text
    result = first.json()
    assert result["assessment"]["classification"] == "HIGH_RISK"
    assert result["assessment"]["risk_score"] is None
    outcomes = {source["name"]: source for source in result["sources"] if source["kind"] == "threat_intelligence"}
    assert outcomes["urlhaus"]["status"] == outcomes["phishtank"]["status"] == "matched"
    assert outcomes["rdap"]["status"] == outcomes["crtsh"]["status"] == "observed"
    assert outcomes["rdap"]["details"]["verdict"] is None
    assert outcomes["abuseipdb"]["status"] == "unsupported_input"
    second = client.post("/api/v1/analyze/url", headers=auth, json=submission)
    assert second.status_code == 201
    sources = {source["name"]: source for source in second.json()["sources"]}
    assert sources["urlhaus"]["details"]["cached"] is True
    assert sources["urlhaus"]["observed_at"] == outcomes["urlhaus"]["observed_at"]
    assert len([call for call in calls if call.url.host == "urlhaus-api.abuse.ch"]) == 1
    with Session(app.state.database.engine) as session:
        rows = session.scalars(select(ThreatIntelligenceResult)).all()
        assert len(rows) == 14
        assert any(row.provider == "rdap" and row.verdict is None for row in rows)
