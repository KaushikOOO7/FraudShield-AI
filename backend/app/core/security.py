import asyncio
import json
import time
from dataclasses import dataclass
from uuid import UUID

import httpx
import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.core.config import Settings
from backend.app.core.errors import APIError

bearer = HTTPBearer(auto_error=False, scheme_name="SupabaseAccessToken")


@dataclass(frozen=True)
class Principal:
    user_id: UUID


class JWTVerifier:
    """Verify issuer-owned keys; never follow token-supplied jku/x5u locations."""

    def __init__(self, settings: Settings, client: httpx.AsyncClient):
        self.settings = settings
        self.client = client
        self._keys: dict[str, jwt.PyJWK] = {}
        self._expires_at = 0.0
        self._last_attempt = float("-inf")
        self._lock = asyncio.Lock()

    async def _refresh_keys(self):
        self._last_attempt = time.monotonic()
        endpoint = f"{self.settings.jwt_issuer}/.well-known/jwks.json"
        try:
            async with self.client.stream("GET", endpoint, headers={"Accept-Encoding": "identity"}, follow_redirects=False) as response:
                if response.status_code != 200:
                    raise ValueError("Invalid JWKS HTTP status")
                if response.headers.get("content-encoding", "identity").lower() != "identity":
                    raise ValueError("Unsupported JWKS encoding")
                payload = bytearray()
                async for chunk in response.aiter_bytes():
                    payload.extend(chunk)
                    if len(payload) > 65536:
                        raise ValueError("JWKS size exceeded")
            document = json.loads(payload)
            if not isinstance(document, dict) or not isinstance(document.get("keys"), list):
                raise ValueError("Invalid JWKS structure")
            if not 1 <= len(document["keys"]) <= 64:
                raise ValueError("Invalid JWKS key count")
            keys = {}
            for data in document["keys"]:
                if not isinstance(data, dict):
                    raise ValueError("Invalid JWK")
                if data.get("kty") not in ("EC", "RSA") or data.get("use", "sig") != "sig":
                    continue
                kid = data.get("kid")
                if not isinstance(kid, str) or not 1 <= len(kid) <= 128 or kid in keys:
                    raise ValueError("Invalid JWK identifier")
                key = jwt.PyJWK.from_dict(data)
                if key.algorithm_name not in ("ES256", "RS256"):
                    continue
                keys[kid] = key
            if not keys:
                raise ValueError("No supported signing keys")
        except (httpx.HTTPError, ValueError, TypeError, jwt.PyJWTError):
            raise APIError(503, "auth_provider_unavailable", "Authentication signing keys are unavailable") from None
        self._keys = keys
        self._expires_at = time.monotonic() + self.settings.jwks_cache_seconds

    async def _get_key(self, kid: str) -> jwt.PyJWK:
        async with self._lock:
            now = time.monotonic()
            if now < self._expires_at and kid in self._keys:
                return self._keys[kid]
            # An unknown kid must not cause unlimited outgoing JWKS requests.
            if now - self._last_attempt >= 30:
                await self._refresh_keys()
            elif now >= self._expires_at:
                raise APIError(503, "auth_provider_unavailable", "Authentication signing keys are unavailable")
            key = self._keys.get(kid)
            if key is None:
                raise APIError(401, "invalid_token", "Invalid access token", {"WWW-Authenticate": "Bearer"})
            return key

    async def verify(self, token: str) -> Principal:
        if not self.settings.jwt_issuer:
            raise APIError(503, "auth_not_configured", "Supabase authentication is not configured")
        try:
            if len(token) > 8192:
                raise ValueError
            header = jwt.get_unverified_header(token)
            algorithm = header.get("alg")
            if header.get("crit"):
                raise ValueError
            if algorithm == "HS256" and self.settings.supabase_jwt_secret:
                key = self.settings.supabase_jwt_secret.get_secret_value()
            elif algorithm in ("ES256", "RS256"):
                kid = header.get("kid")
                if not isinstance(kid, str) or not 1 <= len(kid) <= 128:
                    raise ValueError
                signing_key = await self._get_key(kid)
                if signing_key.algorithm_name != algorithm:
                    raise ValueError
                key = signing_key.key
            else:
                raise ValueError
            claims = jwt.decode(
                token, key=key, algorithms=[algorithm],
                audience=self.settings.jwt_audience, issuer=self.settings.jwt_issuer,
                options={"require": ["exp", "iat", "iss", "aud", "sub", "role"]},
            )
            if claims["role"] != "authenticated":
                raise ValueError
            return Principal(user_id=UUID(claims["sub"]))
        except APIError:
            raise
        except (jwt.PyJWTError, ValueError, TypeError, KeyError, OverflowError):
            raise APIError(401, "invalid_token", "Invalid access token", {"WWW-Authenticate": "Bearer"}) from None


async def current_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> Principal:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise APIError(401, "authentication_required", "An access token is required", {"WWW-Authenticate": "Bearer"})
    return await request.app.state.jwt_verifier.verify(credentials.credentials)
