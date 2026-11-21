import asyncio
import hashlib
import json
import math
import re
import time
from collections import OrderedDict
from threading import Lock
from uuid import UUID, uuid4
from urllib.parse import urlsplit

from backend.app.core.config import Settings
from backend.app.core.errors import error_body


class WindowLimiter:
    """Bounded per-process ingress limiter. Production also needs a gateway limiter."""

    def __init__(self, limit: int, maximum_keys: int = 10000):
        self.limit = limit
        self.maximum_keys = maximum_keys
        self._entries: OrderedDict[str, tuple[int, int]] = OrderedDict()
        self._lock = Lock()

    def allow(self, key: str) -> tuple[bool, int]:
        now = time.time()
        window = int(now // 60)
        hashed_key = hashlib.sha256(key.encode()).hexdigest()
        with self._lock:
            old_window, count = self._entries.pop(hashed_key, (window, 0))
            count = count + 1 if old_window == window else 1
            self._entries[hashed_key] = (window, count)
            if len(self._entries) > self.maximum_keys:
                self._entries.popitem(last=False)
        return count <= self.limit, max(1, math.ceil((window + 1) * 60 - now))


class RequestSecurityMiddleware:
    def __init__(self, app, settings: Settings):
        self.app = app
        self.settings = settings
        self.limiter = WindowLimiter(settings.ip_rate_limit_per_minute)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = {k.lower(): v for k, v in scope.get("headers", [])}
        try:
            request_id = str(UUID(headers.get(b"x-request-id", b"").decode("ascii")))
        except (ValueError, UnicodeDecodeError):
            request_id = str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        max_body_bytes = self.settings.qr_max_upload_bytes + 32768 if scope["path"] == "/api/v1/analyze/qr" else self.settings.max_request_bytes
        if scope["path"] == "/api/v1/analyze/apk":
            max_body_bytes = self.settings.apk_max_upload_bytes + 32768

        async def secure_send(message):
            if message["type"] == "http.response.start":
                response_headers = list(message.get("headers", []))
                response_headers.extend([
                    (b"x-request-id", request_id.encode()),
                    (b"x-content-type-options", b"nosniff"),
                    (b"cache-control", b"no-store"),
                ])
                if self.settings.app_env == "production":
                    response_headers.append((b"strict-transport-security", b"max-age=31536000"))
                message["headers"] = response_headers
            await send(message)

        async def reject(status, code, message, extra_headers=None):
            body = json.dumps(error_body(code, message, request_id)).encode()
            response_headers = [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]
            response_headers.extend(extra_headers or [])
            await secure_send({"type": "http.response.start", "status": status, "headers": response_headers})
            await secure_send({"type": "http.response.body", "body": body})

        if self.settings.app_env == "production" and scope.get("scheme") != "https":
            return await reject(400, "https_required", "HTTPS is required")
        try:
            authority = urlsplit("//" + headers.get(b"host", b"").decode("ascii"))
            host = (authority.hostname or "").casefold()
            if authority.username or authority.password or authority.path:
                raise ValueError
            if not any(pattern == "*" or host == pattern.casefold() or (pattern.startswith("*.") and host.endswith(pattern[1:].casefold())) for pattern in self.settings.allowed_hosts):
                raise ValueError
        except (ValueError, UnicodeDecodeError):
            return await reject(400, "invalid_host", "Invalid Host header")
        if scope["path"].startswith("/api/"):
            peer = (scope.get("client") or ("unknown", 0))[0]
            allowed, retry = self.limiter.allow(peer)
            if not allowed:
                return await reject(429, "rate_limited", "Request rate limit exceeded", [(b"retry-after", str(retry).encode())])
        if headers.get(b"content-encoding", b"identity").lower() != b"identity":
            return await reject(415, "unsupported_encoding", "Compressed request bodies are not supported")
        if b"content-length" in headers:
            try:
                length = int(headers[b"content-length"])
                if length < 0:
                    raise ValueError
            except ValueError:
                return await reject(400, "invalid_content_length", "Invalid Content-Length")
            if length > max_body_bytes:
                return await reject(413, "request_too_large", "Request body exceeds the size limit")
        body = bytearray()
        deadline = time.monotonic() + self.settings.request_body_timeout_seconds
        while True:
            try:
                message = await asyncio.wait_for(receive(), max(0.001, deadline - time.monotonic()))
            except TimeoutError:
                return await reject(408, "request_timeout", "Request body timed out")
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > max_body_bytes:
                return await reject(413, "request_too_large", "Request body exceeds the size limit")
            if not message.get("more_body", False):
                break
        delivered = False

        json_body_route = scope["path"] in (
            "/api/v1/analyze/sms", "/api/v1/analyze/url", "/api/v1/analyze/caller",
            "/api/v1/reports", "/api/v1/watchlist", "/api/v1/alerts/preferences",
        ) or re.fullmatch(r"/api/v1/investigations/[^/]+/interpret", scope["path"])
        if scope["method"] in ("POST", "PATCH") and json_body_route:
            media_type = headers.get(b"content-type", b"").split(b";", 1)[0].strip().lower()
            if media_type != b"application/json":
                return await reject(415, "json_required", "This endpoint requires application/json")

        async def replay_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay_receive, secure_send)
