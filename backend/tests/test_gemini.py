"""Explicit non-production Gemini HTTP fixtures; no live model calls claimed."""
import json
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import select, update, func
from sqlalchemy.orm import Session

from backend.app.database.models import InvestigationEvent, User


def headers(token_factory, **claims):
    return {"Authorization": f"Bearer {token_factory(**claims)}"}


def submit(client, token_factory, corpus_message):
    response = client.post("/api/v1/analyze/sms", headers=headers(token_factory), json={"content": corpus_message(2), "source": "android_share"})
    assert response.status_code == 201
    assert response.json()["findings"]
    return response


def test_missing_gemini_key_returns_no_fabricated_interpretation(api_factory, token_factory, corpus_message):
    client, app, calls = api_factory()
    response = submit(client, token_factory, corpus_message)
    interpreted = client.post(response.headers["Location"] + "/interpret", headers=headers(token_factory), json={"use_gemini": True})
    assert interpreted.status_code == 200
    result = interpreted.json()
    assert result["status"] == "provider_not_configured"
    assert result["model_used"] is None
    assert result["selected_findings"] == result["recommended_actions"] == []
    assert len(calls) == 1
    assert client.get(response.headers["Location"], headers=headers(token_factory)).json() == response.json()
    with Session(app.state.database.engine) as session:
        event = session.scalar(select(InvestigationEvent).where(InvestigationEvent.event_type == "interpretation.checked"))
        assert event.details["status"] == "provider_not_configured"


def test_gemini_opt_in_selects_actual_references_without_raw_content_or_sql_lock(api_factory, token_factory, corpus_message, auth_material):
    app_holder = {}
    def handler(request):
        assert request.url.host == "generativelanguage.googleapis.com"
        assert request.headers["x-goog-api-key"] == "isolated-gemini-key"
        payload = json.loads(request.content)
        content = payload["contents"][0]["parts"][0]["text"]
        assert corpus_message(2) not in content
        facts = json.loads(content)
        # Verify external analysis does not hold a database write lock.
        with Session(app_holder["app"].state.database.engine) as session, session.begin():
            session.execute(update(User).where(User.id == auth_material["user_id"]).values(updated_at=func.now()))
        selection = {"finding_ids": [facts["findings"][0]["id"]], "action_indices": [0]}
        return httpx.Response(200, json={"modelVersion": "gemini-isolated-test-version", "candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": json.dumps(selection)}]}}]})
    client, app, calls = api_factory(provider_handler=handler, gemini_api_key="isolated-gemini-key", gemini_model="gemini-isolated-test-model")
    app_holder["app"] = app
    response = submit(client, token_factory, corpus_message)
    path = response.headers["Location"] + "/interpret"
    result = client.post(path, headers=headers(token_factory), json={"use_gemini": True})
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "available"
    assert result.json()["selected_findings"] == [response.json()["findings"][0]]
    assert result.json()["recommended_actions"] == [response.json()["recommended_actions"][0]]
    assert "isolated-gemini-key" not in result.text
    assert client.get(response.headers["Location"], headers=headers(token_factory)).json() == response.json()
    assert client.post(path, headers=headers(token_factory, sub=str(uuid4())), json={"use_gemini": True}).status_code == 404
    assert len([call for call in calls if call.url.host == "generativelanguage.googleapis.com"]) == 1


@pytest.mark.parametrize("selection", [
    {"finding_ids": [str(uuid4())], "action_indices": [0]},
    {"finding_ids": [], "action_indices": [999]},
    {"finding_ids": [], "action_indices": [0], "invented_risk_score": 99},
    {"finding_ids": [], "action_indices": ["0"]},
])
def test_invented_evidence_or_outputs_rejected(api_factory, token_factory, corpus_message, selection):
    def handler(request):
        return httpx.Response(200, json={"modelVersion": "gemini-isolated-test-version", "candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": json.dumps(selection)}]}}]})
    client, _, _ = api_factory(provider_handler=handler, gemini_api_key="isolated-gemini-key", gemini_model="gemini-isolated-test-model")
    response = submit(client, token_factory, corpus_message)
    interpreted = client.post(response.headers["Location"] + "/interpret", headers=headers(token_factory), json={"use_gemini": True})
    assert interpreted.status_code == 200
    assert interpreted.json()["status"] == "invalid_response"
    assert interpreted.json()["selected_findings"] == []
    assert interpreted.json()["model_used"] is None


def test_gemini_is_not_called_without_explicit_opt_in(api_factory, token_factory, corpus_message):
    client, _, calls = api_factory(gemini_api_key="isolated-gemini-key", gemini_model="gemini-isolated-test-model")
    response = submit(client, token_factory, corpus_message)
    result = client.post(response.headers["Location"] + "/interpret", headers=headers(token_factory), json={"use_gemini": False})
    assert result.json()["status"] == "not_requested"
    assert len(calls) == 1
    assert client.post(response.headers["Location"] + "/interpret", headers=headers(token_factory), json={"use_gemini": "true"}).status_code == 422


def test_interpretation_rejects_non_json_before_external_processing(
    api_factory, token_factory, corpus_message,
):
    client, _, calls = api_factory(
        gemini_api_key="isolated-gemini-key", gemini_model="gemini-isolated-test-model",
    )
    submitted = submit(client, token_factory, corpus_message)
    response = client.post(
        submitted.headers["Location"] + "/interpret",
        headers={**headers(token_factory), "Content-Type": "text/plain"},
        content=json.dumps({"use_gemini": True}),
    )
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "json_required"
    assert not any(call.url.host == "generativelanguage.googleapis.com" for call in calls)
