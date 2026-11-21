"""Clearly labeled non-production validation strings; URLs are not live-threat claims."""
import pytest
from pydantic import ValidationError

from backend.app.schemas.requests import SMSRequest, URLRequest
from backend.app.utils.privacy import redact_text, redact_url
from backend.app.utils.urls import URLValidationError, parse_public_url


@pytest.mark.parametrize("content", [
    "", "   ", "test\x00", "x" * 5001,
    "ISOLATED TEST OTP is 123456", "ISOLATED TEST password=fixture-secret",
    "ISOLATED TEST UPI PIN 1234", "ISOLATED TEST card 4111 1111 1111 1111",
    "ISOLATED TEST account number 12345678901", "https://example.com/?token=isolated-fixture",
])
def test_sms_rejects_invalid_or_sensitive_values(content):
    with pytest.raises(ValidationError):
        SMSRequest(content=content)


def test_redacted_values_and_secret_warnings_are_allowed():
    assert SMSRequest(content="Never share your OTP or UPI PIN.").content
    assert SMSRequest(content="Your OTP is [REDACTED].").content


@pytest.mark.parametrize("url", [
    "javascript:alert(1)", "file:///etc/passwd", "ftp://example.com/file", "example.com",
    "http://localhost/", "http://localhost./", "http://127.0.0.1/", "http://10.0.0.1/",
    "http://169.254.169.254/", "http://[::1]/", "http://[::ffff:127.0.0.1]/",
    "http://[64:ff9b::7f00:1]/", "http://2130706433/", "http://0177.0.0.1/",
    "https://metadata.google.internal/", "https://user:password@example.com/",
    "https://example.com:22/", "https://example.com/\nsecret", "https://example.com/%0d%0a",
    "https://example.com\\@127.0.0.1/", "https://example.com/?otp=123456",
    "https://example.com/?ot%70=123456", "https://example.com/#access_token=test-only",
])
def test_ssrf_and_credentials_lexically_rejected(url):
    with pytest.raises((URLValidationError, ValidationError)):
        URLRequest(url=url)


def test_url_canonicalization_and_unicode_host():
    assert parse_public_url("https://EXAMPLE.com:443#section").normalized == "https://example.com/"
    assert parse_public_url("https://пример.рф/").hostname.startswith("xn--")


def test_evidence_redaction():
    redacted = redact_text("ISOLATED TEST contact 9876543210 or someone@example.com; pay someone@upi")
    for value in ("9876543210", "someone@example.com", "someone@upi"):
        assert value not in redacted
    redacted_url = redact_url("https://example.com/path?customer=isolated-fixture&campaign=private#private-fragment")
    assert "isolated-fixture" not in redacted_url
    assert "private" not in redacted_url
