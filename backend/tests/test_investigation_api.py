"""End-to-end real SMS inference, signed test JWTs, and isolated SQL databases.

SMS source rows are the registered UCI corpus. The cryptographic identity and
HTTP transport are explicitly non-production fixtures, never default credentials.
No live threat verdict is fabricated.
"""
import json
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from backend.app.core.config import PROJECT_ROOT, Settings
from backend.app.core.errors import APIError
from backend.app.database.connection import Database
from backend.app.database.migrate import apply_migrations
from backend.app.database.models import (
    AuditLog, Domain, Evidence, EvidenceSource, Investigation, InvestigationEvent,
    ModelPrediction, ModelVersion, RiskAssessment, ThreatIntelligenceResult, URLIndicator,
    User,
)
from backend.app.main import create_app
from backend.app.schemas.investigation import InvestigationResponse
from backend.tests.http_client import TestClient
from backend.tests.fixtures import registered_sms_path


def auth_headers(token_factory, **claims):
    return {"Authorization": f"Bearer {token_factory(**claims)}"}


@pytest.mark.model
def test_android_sms_actual_inference_storage_history_and_delete(api_factory, corpus_message, token_factory):
    client, app, calls = api_factory()
    headers = auth_headers(token_factory)
    response = client.post("/api/v1/analyze/sms", headers=headers, json={"content": corpus_message(2), "source": "android_share", "device_id": None})
    assert response.status_code == 201, response.text
    result = InvestigationResponse.model_validate(response.json())
    assert result.models[0].label == "spam"
    assert result.models[0].status == "available"
    assert result.models[0].version == app.state.sms_model.manifest["version"]
    assert result.assessment.classification == "EXERCISE_CAUTION"
    assert result.assessment.risk_score is None
    assert result.models[0].confidence is None
    assert response.headers["Location"].endswith(str(result.investigation_id))
    assert all(request.url.path.endswith("jwks.json") for request in calls)
    with Session(app.state.database.engine) as session:
        assert session.scalar(select(func.count()).select_from(Investigation)) == 1
        assert session.scalar(select(func.count()).select_from(ModelPrediction)) == 1
        assert session.scalar(select(ModelVersion)).artifact_sha256 == app.state.sms_model.manifest["artifact_sha256"]
        assert session.scalar(select(RiskAssessment)).risk_score is None
    stored = client.get(response.headers["Location"], headers=headers)
    assert stored.status_code == 200
    assert stored.json() == response.json()
    listing = client.get("/api/v1/investigations", headers=headers).json()
    assert len(listing["items"]) == 1
    assert listing["has_more"] is False
    assert client.delete(response.headers["Location"], headers=headers).status_code == 204
    assert client.get(response.headers["Location"], headers=headers).status_code == 404
    assert client.get("/api/v1/investigations", headers=headers).json()["items"] == []
    with Session(app.state.database.engine) as session:
        for model in (Investigation, Evidence, EvidenceSource, InvestigationEvent, ModelPrediction, RiskAssessment):
            assert session.scalar(select(func.count()).select_from(model)) == 0
        assert session.scalar(select(func.count()).select_from(AuditLog)) > 0


def test_cross_user_cannot_read_delete_or_list_investigations(api_factory, corpus_message, token_factory):
    client, _, _ = api_factory()
    owner = auth_headers(token_factory)
    another = auth_headers(token_factory, sub=str(uuid4()))
    response = client.post("/api/v1/analyze/sms", headers=owner, json={"content": corpus_message(0), "source": "android_manual"})
    assert response.status_code == 201, response.text
    path = response.headers["Location"]
    assert client.get(path, headers=another).status_code == 404
    assert client.delete(path, headers=another).status_code == 404
    assert client.get("/api/v1/investigations", headers=another).json()["items"] == []
    assert client.get(path, headers=owner).status_code == 200


def test_url_untrained_and_missing_providers_are_explicit(api_factory, token_factory):
    client, app, calls = api_factory()
    headers = auth_headers(token_factory)
    response = client.post("/api/v1/analyze/url", headers=headers, json={"url": "https://example.com/", "source": "android_share", "use_threat_intelligence": True})
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["status"] == "partial"
    assert result["models"][0]["status"] == "model_not_trained"
    assert result["models"][0]["label"] is None
    provider_sources = [source for source in result["sources"] if source["kind"] == "threat_intelligence"]
    assert len(provider_sources) == len(app.state.intelligence.providers)
    assert all(source["status"] == "provider_not_configured" and source["details"]["verdict"] is None for source in provider_sources)
    assert result["assessment"]["classification"] == "EXERCISE_CAUTION"
    assert len(calls) == 1
    assert client.delete(response.headers["Location"], headers=headers).status_code == 204
    with Session(app.state.database.engine) as session:
        for model in (URLIndicator, Domain, ThreatIntelligenceResult, EvidenceSource):
            assert session.scalar(select(func.count()).select_from(model)) == 0


@pytest.mark.model
def test_genuine_sms_url_routes_without_treating_dataset_urls_as_live_threats(api_factory, corpus_message, token_factory):
    client, _, calls = api_factory()
    response = client.post("/api/v1/analyze/sms", headers=auth_headers(token_factory), json={"content": corpus_message(12), "source": "android_share", "use_threat_intelligence": True})
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["subject"]["attributes"]["analyzed_url_count"] == 1
    assert result["models"][0]["status"] == "available"
    assert result["models"][1]["status"] == "model_not_trained"
    assert not any(finding["verification_status"] == "provider_report" for finding in result["findings"])
    assert len(calls) == 1


def test_missing_model_never_substitutes_fake_inference(api_factory, corpus_message, token_factory, tmp_path):
    client, _, _ = api_factory(sms_model_dir=tmp_path / "no-model")
    response = client.post("/api/v1/analyze/sms", headers=auth_headers(token_factory), json={"content": corpus_message(0)})
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["status"] == "partial"
    assert result["models"][0]["status"] == "model_not_trained"
    assert result["models"][0]["decision_score"] is None
    assert result["assessment"]["classification"] == "EXERCISE_CAUTION"


def test_empty_history_is_actual_empty_result(api_factory, token_factory):
    client, _, _ = api_factory()
    response = client.get("/api/v1/investigations", headers=auth_headers(token_factory))
    assert response.status_code == 200
    assert response.json() == {"items": [], "limit": 20, "offset": 0, "has_more": False}


def test_secret_validation_errors_do_not_echo_values(api_factory, token_factory):
    client, app, _ = api_factory()
    response = client.post("/api/v1/analyze/sms", headers=auth_headers(token_factory), json={"content": "ISOLATED TEST OTP is 123456"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "sensitive_input"
    assert "123456" not in response.text
    assert "ISOLATED TEST OTP" not in response.text
    with Session(app.state.database.engine) as session:
        assert session.scalar(select(func.count()).select_from(Investigation)) == 0


def test_unknown_field_names_do_not_reflect_sensitive_text(api_factory, token_factory, corpus_message):
    client, _, _ = api_factory()
    response = client.post("/api/v1/analyze/sms", headers=auth_headers(token_factory), json={"content": corpus_message(0), "ISOLATED-PRIVATE-KEY-123456": "private"})
    assert response.status_code == 422
    assert "123456" not in response.text
    assert response.json()["error"]["details"][0]["field"] == "body.unknown_field"


def test_unknown_device_does_not_create_a_fake_registration(api_factory, corpus_message, token_factory):
    client, app, _ = api_factory()
    response = client.post("/api/v1/analyze/sms", headers=auth_headers(token_factory), json={"content": corpus_message(0), "device_id": str(uuid4())})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "device_not_found"
    with Session(app.state.database.engine) as session:
        assert session.scalar(select(func.count()).select_from(Investigation)) == 0


def test_storage_failure_rolls_back_before_returning_success(api_factory, corpus_message, token_factory, monkeypatch):
    from backend.app.database.repositories import InvestigationRepository
    original = InvestigationRepository.create
    def failing(self, *args, **kwargs):
        original(self, *args, **kwargs)
        raise APIError(503, "database_unavailable", "Isolated failure fixture")
    monkeypatch.setattr(InvestigationRepository, "create", failing)
    client, app, _ = api_factory()
    response = client.post("/api/v1/analyze/sms", headers=auth_headers(token_factory), json={"content": corpus_message(0)})
    assert response.status_code == 503
    with Session(app.state.database.engine) as session:
        assert session.scalar(select(func.count()).select_from(Investigation)) == 0
        assert session.scalar(select(func.count()).select_from(ModelPrediction)) == 0


def test_analysis_does_not_hold_an_open_database_write_transaction(api_factory, corpus_message, token_factory, auth_material):
    client, app, _ = api_factory()
    original = app.state.sms_service.analyze
    async def inspect_lock(*args, **kwargs):
        # A real independent SQL write during analysis would fail if the request
        # held SQLite's write lock while waiting on intelligence providers.
        with Session(app.state.database.engine) as session, session.begin():
            session.execute(update(User).where(User.id == auth_material["user_id"]).values(updated_at=func.now()))
        return await original(*args, **kwargs)
    app.state.sms_service.analyze = inspect_lock
    response = client.post("/api/v1/analyze/sms", headers=auth_headers(token_factory), json={"content": corpus_message(0)})
    assert response.status_code == 201, response.text


def test_system_status_does_not_claim_configured_keys_were_verified(api_factory, token_factory):
    client, _, _ = api_factory(virustotal_api_key="isolated-test-key-do-not-leak")
    response = client.get("/api/v1/system/status", headers=auth_headers(token_factory))
    assert response.status_code == 200
    result = response.json()
    assert result["database"]["status"] == "connected"
    assert result["sms_model"]["status"] == "available"
    assert next(provider for provider in result["providers"] if provider["name"] == "virustotal")["status"] == "configured_not_verified"
    assert "isolated-test-key-do-not-leak" not in response.text
    assert result["capabilities"]["langgraph"] == "not_implemented"


def test_expired_investigation_is_hidden_before_retention_cleanup(api_factory, corpus_message, token_factory):
    client, app, _ = api_factory()
    headers = auth_headers(token_factory)
    response = client.post("/api/v1/analyze/sms", headers=headers, json={"content": corpus_message(0)})
    assert response.status_code == 201
    with Session(app.state.database.engine) as session, session.begin():
        row = session.get(Investigation, UUID(response.json()["investigation_id"]))
        row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    assert client.get(response.headers["Location"], headers=headers).status_code == 404
    assert client.get("/api/v1/investigations", headers=headers).json()["items"] == []
