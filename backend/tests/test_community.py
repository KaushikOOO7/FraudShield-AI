"""Non-production user/URL/credential fixtures; no fake reports in production."""
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.database.models import CommunityReport, Investigation, SecurityAlert, Watchlist
from backend.app.database.retention import purge_expired


def headers(token_factory, **claims):
    return {"Authorization": f"Bearer {token_factory(**claims)}"}


def test_empty_user_record_lists_and_auth(api_factory, token_factory):
    client, _, _ = api_factory()
    for path in ("/api/v1/reports", "/api/v1/watchlist", "/api/v1/alerts"):
        assert client.get(path).status_code == 401
        response = client.get(path, headers=headers(token_factory))
        assert response.status_code == 200
        assert response.json() == {"items": [], "limit": 20, "offset": 0, "has_more": False}


def test_report_is_unreviewed_redacted_owned_and_persisted(api_factory, token_factory):
    client, app, _ = api_factory()
    owner, other = headers(token_factory), headers(token_factory, sub=str(uuid4()))
    response = client.post("/api/v1/reports", headers=owner, json={"subject_type": "url", "subject": "https://example.com/?reference=isolated-private-value", "description": "ISOLATED TEST REPORT contact fixture@example.com"})
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["moderation_status"] == "unreviewed"
    assert result["verified_at"] is None
    assert "isolated-private-value" not in response.text
    assert "fixture@example.com" not in response.text
    assert client.get(response.headers["Location"], headers=owner).json() == result
    assert client.get(response.headers["Location"], headers=other).status_code == 404
    assert client.get("/api/v1/reports", headers=other).json()["items"] == []
    assert client.get("/api/v1/reports", headers=owner).json()["items"] == [result]
    with Session(app.state.database.engine) as session:
        stored = session.get(CommunityReport, UUID(result["id"]))
        assert stored.moderation_status == "unreviewed" and stored.verified_at is None


@pytest.mark.parametrize("submission", [
    {"subject_type": "url", "subject": "http://127.0.0.1", "description": "ISOLATED REPORT"},
    {"subject_type": "sms", "subject": "OTP is 123456", "description": "ISOLATED REPORT"},
    {"subject_type": "sms", "subject": "ISOLATED REPORT", "description": "password=isolated-secret"},
    {"subject_type": "sms", "subject": "ISOLATED REPORT", "description": "text", "moderation_status": "approved"},
])
def test_report_validation_and_no_moderation_forgery(api_factory, token_factory, submission):
    client, app, _ = api_factory()
    response = client.post("/api/v1/reports", headers=headers(token_factory), json=submission)
    assert response.status_code == 422
    assert "123456" not in response.text and "isolated-secret" not in response.text
    with Session(app.state.database.engine) as session:
        assert session.scalar(select(func.count()).select_from(CommunityReport)) == 0


def test_watchlist_idempotent_normalized_owner_scoped_delete(api_factory, token_factory):
    client, app, _ = api_factory()
    owner, other = headers(token_factory), headers(token_factory, sub=str(uuid4()))
    submission = {"indicator_type": "url", "value": "https://example.com/?reference=isolated-value"}
    first = client.post("/api/v1/watchlist", headers=owner, json=submission)
    assert first.status_code == 201, first.text
    again = client.post("/api/v1/watchlist", headers=owner, json=submission)
    assert again.status_code == 200 and again.json() == first.json()
    assert "isolated-value" not in first.text
    assert client.get("/api/v1/watchlist", headers=owner).json()["items"] == [first.json()]
    assert client.get("/api/v1/watchlist", headers=other).json()["items"] == []
    path = f"/api/v1/watchlist/{first.json()['id']}"
    assert client.delete(path, headers=other).status_code == 404
    assert client.delete(path, headers=owner).status_code == 204
    assert client.delete(path, headers=owner).status_code == 404
    with Session(app.state.database.engine) as session:
        assert session.scalar(select(func.count()).select_from(Watchlist)) == 0


@pytest.mark.parametrize("kind,value", [("domain", "example.com"), ("phone", "+919876543210"), ("apk_sha256", "a" * 64)])
def test_watchlist_supported_indicator_shapes(api_factory, token_factory, kind, value):
    client, _, _ = api_factory()
    response = client.post("/api/v1/watchlist", headers=headers(token_factory), json={"indicator_type": kind, "value": value})
    assert response.status_code == 201, response.text
    if kind == "phone":
        assert value not in response.text and "3210" in response.json()["redacted_value"]


@pytest.mark.parametrize("kind,value", [("domain", "localhost"), ("url", "file:///etc/passwd"), ("phone", "123"), ("apk_sha256", "not-a-hash")])
def test_watchlist_invalid_indicators_fail(api_factory, token_factory, kind, value):
    client, _, _ = api_factory()
    assert client.post("/api/v1/watchlist", headers=headers(token_factory), json={"indicator_type": kind, "value": value}).status_code == 422


@pytest.mark.model
def test_alerts_require_opt_in_and_real_high_risk_evidence(api_factory, token_factory):
    client, app, _ = api_factory()
    owner, other = headers(token_factory), headers(token_factory, sub=str(uuid4()))
    # Explicit non-production rule fixture; no actual OTP/credential is supplied.
    content = "ISOLATED RULE TEST: Send your OTP and transfer payment to police or face arrest."
    def analyze():
        response = client.post("/api/v1/analyze/sms", headers=owner, json={"content": content})
        assert response.status_code == 201, response.text
        assert response.json()["assessment"]["classification"] == "HIGH_RISK"
        return response
    analyze()
    assert client.get("/api/v1/alerts", headers=owner).json()["items"] == []
    preferences = client.patch("/api/v1/alerts/preferences", headers=owner, json={"high_risk_alerts": True})
    assert preferences.status_code == 200
    assert preferences.json() == {"high_risk_alerts": True, "delivery": "in_app_history"}
    response = analyze()
    alerts = client.get("/api/v1/alerts", headers=owner).json()["items"]
    assert len(alerts) == 1
    assert alerts[0]["investigation_id"] == response.json()["investigation_id"]
    assert alerts[0]["severity"] == "high"
    assert alerts[0]["message"] == response.json()["assessment"]["explanation"]
    assert client.get("/api/v1/alerts", headers=other).json()["items"] == []
    client.patch("/api/v1/alerts/preferences", headers=owner, json={"high_risk_alerts": False})
    analyze()
    assert len(client.get("/api/v1/alerts", headers=owner).json()["items"]) == 1
    assert client.delete(response.headers["Location"], headers=owner).status_code == 204
    assert client.get("/api/v1/alerts", headers=owner).json()["items"] == []
    with Session(app.state.database.engine) as session:
        assert session.scalar(select(func.count()).select_from(SecurityAlert)) == 0


def test_preferences_require_explicit_boolean(api_factory, token_factory):
    client, _, _ = api_factory()
    assert client.patch("/api/v1/alerts/preferences", headers=headers(token_factory), json={"high_risk_alerts": "true"}).status_code == 422
    assert client.patch("/api/v1/alerts/preferences", headers={**headers(token_factory), "Content-Type": "text/plain"}, content="text").status_code == 415


def test_reports_expire_without_manufacturing_reputation(api_factory, token_factory):
    client, app, _ = api_factory()
    owner = headers(token_factory)
    response = client.post("/api/v1/reports", headers=owner, json={"subject_type": "domain", "subject": "example.com", "description": "ISOLATED NON-PRODUCTION REPORT"})
    assert response.status_code == 201
    with Session(app.state.database.engine) as session, session.begin():
        session.get(CommunityReport, UUID(response.json()["id"])).created_at = datetime.now(timezone.utc) - timedelta(days=31)
    assert client.get(response.headers["Location"], headers=owner).status_code == 404
    assert client.get("/api/v1/reports", headers=owner).json()["items"] == []
    assert purge_expired(app.state.database)["community_reports_deleted"] == 1
