"""Isolated non-production JWT/transport fixtures. No real users or live provider claims."""
import json
import time
from uuid import uuid4

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from backend.tests.http_client import TestClient

from backend.app.core.config import Settings
from backend.app.main import create_app
from backend.app.database.connection import Database
from backend.app.database.migrate import apply_migrations
from backend.tests.fixtures import registered_sms_path


@pytest.fixture
def corpus_message():
    records = [json.loads(line) for line in registered_sms_path().read_text().splitlines()]
    return lambda source_line: next(record["content"] for record in records if record["source_line"] == source_line)


@pytest.fixture
def api_factory(tmp_path, auth_material):
    """Real ASGI lifecycle/SQL/model with only JWKS HTTP isolated from networking."""
    opened_clients = []
    def create(provider_handler=None, **options):
        database_path = tmp_path / f"api-{len(opened_clients)}.sqlite3"
        settings = Settings(
            app_env="test", database_url=f"sqlite:///{database_path}",
            supabase_url="https://isolated-fixture.supabase.co", _env_file=None, **options,
        )
        database = Database(settings)
        apply_migrations(database.engine)
        database.dispose()
        calls = []
        def handler(request):
            calls.append(request)
            if request.url.path.endswith("/.well-known/jwks.json"):
                return httpx.Response(200, json={"keys": [auth_material["jwk"]]})
            if provider_handler is not None:
                return provider_handler(request)
            raise AssertionError("Unexpected live-provider request in isolated API fixture")
        app = create_app(settings, http_transport=httpx.MockTransport(handler))
        client = TestClient(app)
        client.__enter__()
        opened_clients.append(client)
        return client, app, calls
    yield create
    for client in reversed(opened_clients):
        client.__exit__(None, None, None)


@pytest.fixture
def auth_material():
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_jwk = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(private_key.public_key()))
    public_jwk.update({"kid": "isolated-test-key", "alg": "ES256", "use": "sig"})
    return {"private_key": private_key, "jwk": public_jwk, "user_id": uuid4(), "issuer": "https://isolated-fixture.supabase.co/auth/v1"}


@pytest.fixture
def token_factory(auth_material):
    def make_token(**overrides):
        claims = {
            "iss": auth_material["issuer"], "aud": "authenticated",
            "sub": str(auth_material["user_id"]), "role": "authenticated",
            "iat": int(time.time()) - 5, "exp": int(time.time()) + 300,
        }
        claims.update(overrides)
        return jwt.encode(claims, auth_material["private_key"], algorithm="ES256", headers={"kid": "isolated-test-key"})
    return make_token


@pytest.fixture
def auth_client(auth_material):
    calls = []

    def transport(request):
        calls.append(request)
        if request.url.path.endswith("/.well-known/jwks.json"):
            return httpx.Response(200, json={"keys": [auth_material["jwk"]]})
        raise AssertionError("Unexpected outbound request in isolated auth test")

    settings = Settings(app_env="test", supabase_url="https://isolated-fixture.supabase.co", _env_file=None)
    with TestClient(create_app(settings, http_transport=httpx.MockTransport(transport))) as client:
        yield client, calls
