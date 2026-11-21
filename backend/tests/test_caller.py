"""Explicit non-production phone-format fixtures; no real reputation asserted."""
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from backend.app.database.models import Investigation


def test_caller_format_partial_masked_storage_and_permissions(api_factory, token_factory):
    client, app, calls = api_factory()
    owner = {"Authorization": f"Bearer {token_factory()}"}
    response = client.post("/api/v1/analyze/caller", headers=owner, json={"phone_number": "9876543210", "source": "android_manual", "use_threat_intelligence": True})
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["status"] == "partial"
    assert "9876543210" not in response.text
    assert result["models"] == [] and result["assessment"]["risk_score"] is None
    assert result["assessment"]["classification"] == "EXERCISE_CAUTION"
    assert result["sources"][1]["status"] == "provider_not_configured"
    assert len(calls) == 1
    assert client.get(response.headers["Location"], headers=owner).json() == result
    assert client.get(response.headers["Location"], headers={"Authorization": f"Bearer {token_factory(sub=str(uuid4()))}"}).status_code == 404
    with Session(app.state.database.engine) as session:
        assert "9876543210" not in str(session.get(Investigation, UUID(result["investigation_id"])).result)
    assert client.delete(response.headers["Location"], headers=owner).status_code == 204


@pytest.mark.parametrize("value", ["123", "00123456789", "text", "+" + "1" * 18])
def test_caller_validation_rejects_invalid_shape(api_factory, token_factory, value):
    client, _, _ = api_factory()
    assert client.post("/api/v1/analyze/caller", headers={"Authorization": f"Bearer {token_factory()}"}, json={"phone_number": value}).status_code == 422
