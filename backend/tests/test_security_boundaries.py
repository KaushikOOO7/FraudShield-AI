import asyncio
import json
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from backend.app.core.config import Settings
from backend.app.core.middleware import RequestSecurityMiddleware
from backend.app.intelligence.google_safe_browsing import GoogleSafeBrowsing
from backend.app.main import create_app
from backend.app.schemas.requests import SMSRequest
from backend.tests.http_client import TestClient


def test_streaming_body_limit_cannot_be_bypassed_by_content_length():
    async def run():
        messages = iter([
            {"type": "http.request", "body": b"x" * 600, "more_body": True},
            {"type": "http.request", "body": b"x" * 600, "more_body": False},
        ])
        sent = []
        async def receive(): return next(messages)
        async def send(message): sent.append(message)
        async def never_app(scope, receive, send): raise AssertionError("Oversized input must not reach the app")
        settings = Settings(app_env="test", max_request_bytes=1024, _env_file=None)
        scope = {"type": "http", "method": "POST", "path": "/api/v1/analyze/sms", "scheme": "http", "headers": [(b"host", b"testserver"), (b"content-length", b"5")], "client": ("127.0.0.1", 1)}
        await RequestSecurityMiddleware(never_app, settings)(scope, receive, send)
        assert sent[0]["status"] == 413
        assert json.loads(sent[1]["body"])["error"]["code"] == "request_too_large"
    asyncio.run(run())


def test_host_and_json_errors_use_the_stable_envelope():
    with TestClient(create_app(Settings(app_env="test", _env_file=None))) as client:
        host = client.get("/health", headers={"Host": "untrusted.example"})
        assert host.status_code == 400
        assert host.json()["error"]["code"] == "invalid_host"
        media = client.post("/api/v1/analyze/sms", content=b"not JSON", headers={"Content-Type": "text/plain"})
        assert media.status_code == 415
        assert media.json()["error"]["code"] == "json_required"


def test_opt_in_requires_a_json_boolean():
    with pytest.raises(ValidationError):
        SMSRequest(content="ISOLATED VALIDATION FIXTURE", use_threat_intelligence="true")


def test_500_response_is_sanitized_and_has_request_id():
    app = create_app(Settings(app_env="test", _env_file=None))
    @app.get("/isolated-error-fixture")
    async def broken():
        raise RuntimeError("DO-NOT-LEAK-ISOLATED-CREDENTIAL")
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/isolated-error-fixture")
        assert response.status_code == 500
        assert response.json()["error"]["code"] == "internal_error"
        assert response.headers["X-Request-ID"] == response.json()["error"]["request_id"]
        assert "DO-NOT-LEAK" not in response.text


def test_production_ssl_check_cannot_be_satisfied_by_password_text():
    with pytest.raises(ValidationError):
        Settings(app_env="production", database_url="postgresql+psycopg://fixture:sslmode=verify-full@example.com/db", supabase_url="https://isolated-fixture.supabase.co", allowed_hosts=["api.example.com"], _env_file=None)


def test_provider_redirects_remain_disabled_even_with_permissive_client():
    async def run():
        calls = []
        def handler(request):
            calls.append(request)
            return httpx.Response(302, headers={"Location": "http://127.0.0.1/"})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=True) as client:
            provider = GoogleSafeBrowsing(SecretStr("isolated-test-key"), client, 1)
            result = await provider.lookup("https://example.com/")
            assert result.status == "provider_error"
            assert result.verdict is None
            assert len(calls) == 1
    asyncio.run(run())
