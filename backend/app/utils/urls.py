import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit, urlunsplit

import idna

from backend.app.utils.privacy import URL_PATTERN, has_sensitive_values


class URLValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedURL:
    normalized: str
    hostname: str
    scheme: str
    path: str
    ip_literal: bool


def public_ip(value: str):
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return None
    if not address.is_global:
        raise URLValidationError("Non-public network addresses are not supported")
    if isinstance(address, ipaddress.IPv6Address):
        embedded = address.ipv4_mapped or address.sixtofour
        if embedded and not embedded.is_global:
            raise URLValidationError("Non-public embedded IPv4 address")
        if address.teredo and any(not ip.is_global for ip in address.teredo):
            raise URLValidationError("Non-public Teredo address")
        if address in ipaddress.ip_network("64:ff9b::/96") and not ipaddress.IPv4Address(int(address) & 0xffffffff).is_global:
            raise URLValidationError("Non-public translated IPv4 address")
    return address


def parse_public_url(value: str) -> ParsedURL:
    if not value or len(value) > 2048 or re.search(r"[\x00-\x20\x7f\\]", value):
        raise URLValidationError("Malformed URL")
    if re.search(r"[\x00-\x1f\x7f\\]", unquote(unquote(value))):
        raise URLValidationError("Encoded control characters are not supported")
    if has_sensitive_values(value):
        raise URLValidationError("Credentials must be removed before submitting a URL")
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise URLValidationError("An absolute HTTP or HTTPS URL is required")
        if parsed.username is not None or parsed.password is not None:
            raise URLValidationError("Credentials in URLs are not supported")
        if parsed.port not in (None, 80, 443):
            raise URLValidationError("Only standard web ports are supported")
        hostname = parsed.hostname.rstrip(".").casefold()
        if "%" in hostname:
            raise URLValidationError("Encoded hosts and address zones are not supported")
        address = public_ip(hostname)
        if address is None:
            hostname = idna.encode(hostname, uts46=False, std3_rules=True).decode("ascii")
            if len(hostname) > 253 or "." not in hostname:
                raise URLValidationError("A fully qualified public host is required")
            if hostname == "localhost" or hostname.endswith((".localhost", ".local", ".internal", ".lan", ".home", ".onion", ".invalid", ".test", ".example")):
                raise URLValidationError("Local or reserved hosts are not supported")
            if hostname.rsplit(".", 1)[1].isdigit():
                raise URLValidationError("Ambiguous numeric host")
        authority = f"[{hostname}]" if ":" in hostname else hostname
        if parsed.port and parsed.port != (443 if parsed.scheme == "https" else 80):
            authority += f":{parsed.port}"
        path = parsed.path or "/"
        return ParsedURL(urlunsplit((parsed.scheme, authority, path, parsed.query, "")), hostname, parsed.scheme, path, address is not None)
    except (ValueError, idna.IDNAError) as exc:
        if isinstance(exc, URLValidationError):
            raise
        raise URLValidationError("Malformed URL") from None


def extract_urls(content: str, maximum: int = 5) -> tuple[list[str], int]:
    candidates = []
    for match in URL_PATTERN.finditer(content):
        value = match.group().rstrip(".,;:!?)]}")
        if value.lower().startswith("www."):
            value = "https://" + value
        if value not in candidates:
            candidates.append(value)
    return candidates[:maximum], len(candidates)
