import json

import pytest
from backend.tests.http_client import TestClient
from pydantic import ValidationError

from backend.app.core.config import Settings
from backend.app.main import create_app


def test_startup_health_and_openapi():
    with TestClient(create_app(Settings(app_env="test", _env_file=None))) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["service"] == "FraudShield AI"
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-request-id"]
        assert client.get("/openapi.json").json()["info"]["version"] == "0.1.0"


def test_unknown_route_is_sanitized():
    with TestClient(create_app(Settings(app_env="test", _env_file=None))) as client:
        response = client.get("/api/v1/not-implemented?secret=do-not-reflect")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"
        assert "do-not-reflect" not in response.text


def test_oversized_and_encoded_body_rejected():
    with TestClient(create_app(Settings(app_env="test", max_request_bytes=1024, _env_file=None))) as client:
        assert client.post("/api/v1/analyze/sms", content=b"x" * 1025).status_code == 413
        response = client.post("/api/v1/analyze/sms", content=b"abc", headers={"Content-Encoding": "gzip"})
        assert response.status_code == 415


def test_ingress_rate_limit():
    with TestClient(create_app(Settings(app_env="test", ip_rate_limit_per_minute=1, _env_file=None))) as client:
        assert client.get("/api/v1/missing").status_code == 404
        response = client.get("/api/v1/missing")
        assert response.status_code == 429
        assert int(response.headers["retry-after"]) > 0


def test_unconfigured_secrets_remain_unconfigured():
    settings = Settings(supabase_url="", virustotal_api_key="", _env_file=None)
    assert settings.supabase_url is None
    assert settings.virustotal_api_key is None


@pytest.mark.parametrize("options", [
    {"app_env": "production"},
    {"cors_origins": ["*"]},
    {"supabase_url": "http://example.com"},
    {"supabase_url": "https://user:password@example.com"},
    {"supabase_jwt_secret": "too-short"},
])
def test_insecure_configurations_rejected(options):
    with pytest.raises(ValidationError):
        Settings(**options, _env_file=None)
