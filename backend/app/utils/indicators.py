import hashlib
import re

from backend.app.utils.privacy import has_sensitive_values, redact_text, redact_url
from backend.app.utils.urls import parse_public_url


def normalize_phone(value: str) -> str:
    value = re.sub(r"[ ()-]", "", value.strip())
    if re.fullmatch(r"[6-9][0-9]{9}", value):
        value = "+91" + value
    if not re.fullmatch(r"\+[1-9][0-9]{7,14}", value):
        raise ValueError("Use E.164 or a ten-digit Indian mobile number")
    return value


def normalized_indicator(kind: str, value: str) -> tuple[str, str]:
    if has_sensitive_values(value):
        raise ValueError("Remove sensitive credentials")
    if kind == "url":
        normalized = parse_public_url(value).normalized
        redacted = redact_url(normalized)
    elif kind == "domain":
        parsed = parse_public_url("https://" + value.strip() + "/")
        if parsed.ip_literal or parsed.hostname != value.strip().rstrip(".").casefold() or "/" in value:
            raise ValueError("Use an exact ASCII public hostname")
        normalized = redacted = parsed.hostname
    elif kind == "phone":
        normalized = normalize_phone(value)
        redacted = normalized[:3] + "*" * (len(normalized) - 7) + normalized[-4:]
    elif kind == "apk_sha256":
        if not re.fullmatch(r"[0-9a-fA-F]{64}", value):
            raise ValueError("Use a SHA-256 hex digest")
        normalized = redacted = value.lower()
    elif kind == "sms":
        normalized = value.strip()
        if not normalized:
            raise ValueError("Subject cannot be blank")
        redacted = redact_text(normalized)
    else:
        raise ValueError("Unsupported indicator type")
    return redacted, hashlib.sha256(normalized.encode()).hexdigest()
