import json
import time
from uuid import uuid4

import httpx
import jwt
import pytest
from backend.tests.http_client import TestClient

from backend.app.core.config import Settings
from backend.app.main import create_app


def test_authentication_required(auth_client):
    client, calls = auth_client
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert calls == []


def test_real_signed_jwt_and_jwks_cache(auth_client, token_factory, auth_material):
    client, calls = auth_client
    headers = {"Authorization": f"Bearer {token_factory()}"}
    for _ in range(2):
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200
        assert response.json()["user_id"] == str(auth_material["user_id"])
    assert len(calls) == 1


@pytest.mark.parametrize("overrides", [
    {"exp": 1}, {"iss": "https://wrong-issuer.example/auth/v1"},
    {"aud": "wrong-audience"}, {"role": "service_role"},
    {"role": "anon"}, {"sub": "not-a-uuid"}, {"iat": int(time.time()) + 300},
])
def test_invalid_claims_rejected(auth_client, token_factory, overrides):
    client, _ = auth_client
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_factory(**overrides)}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


def test_unsigned_and_tampered_tokens_rejected(auth_client, token_factory):
    client, _ = auth_client
    unsigned = jwt.encode({"sub": str(uuid4())}, key="", algorithm="none")
    token = token_factory()
    parts = token.split(".")
    parts[1] = jwt.utils.base64url_encode(json.dumps({"sub": str(uuid4())}).encode()).decode()
    for value in (unsigned, ".".join(parts), "not-a-token"):
        assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {value}"}).status_code == 401


def test_missing_supabase_configuration_returns_unavailable():
    with TestClient(create_app(Settings(app_env="test", _env_file=None))) as client:
        response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer test-only-invalid-token"})
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "auth_not_configured"


def test_broken_jwks_is_not_clean_authentication(token_factory):
    settings = Settings(app_env="test", supabase_url="https://isolated-fixture.supabase.co", _env_file=None)
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"keys": []}))
    with TestClient(create_app(settings, http_transport=transport)) as client:
        assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_factory()}"}).status_code == 503


def test_unknown_key_does_not_force_outbound_requests(auth_client, token_factory, auth_material):
    client, calls = auth_client
    client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_factory()}"})
    invalid = jwt.encode({"sub": str(uuid4())}, auth_material["private_key"], algorithm="ES256", headers={"kid": "unknown-test-key"})
    for _ in range(3):
        assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {invalid}"}).status_code == 401
    assert len(calls) == 1
