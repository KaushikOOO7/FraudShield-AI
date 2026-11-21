import re
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

SENSITIVE_QUERY_KEYS = {
    "otp", "pin", "upi_pin", "password", "passcode", "cvv", "cvc", "card_number",
    "account_number", "access_token", "refresh_token", "token", "session", "session_id",
    "authorization", "auth", "cookie", "secret", "signature", "api_key", "apikey",
}
URL_PATTERN = re.compile(r"\b(?:https?://|www\.)[^\s<>\"']+", re.IGNORECASE)


def luhn_valid(digits: str) -> bool:
    total = 0
    for index, value in enumerate(reversed(digits)):
        number = int(value)
        if index % 2:
            number = number * 2
            if number > 9:
                number -= 9
        total += number
    return total % 10 == 0


def has_sensitive_values(content: str) -> bool:
    text = unquote(unquote(content))
    labels = re.finditer(r"\b(?:otp|one[ -]?time (?:password|passcode)|verification code|upi\s*pin|pin|password|passcode|cvv|cvc)\b", text, re.IGNORECASE)
    for match in labels:
        nearby = text[max(0, match.start() - 40):match.end() + 64]
        if re.search(r"(?<!\d)(?:\d[ -]?){4,8}(?!\d)", nearby):
            return True
    if re.search(r"\b(?:password|passcode|pin|cvv|cvc)\s*(?:[:=]|is\b)\s*[\"']?(?!\[REDACTED)[\w@!#$%*+.-]{3,}", text, re.IGNORECASE):
        return True
    if re.search(r"\b(?:account|a/c|acct)\s*(?:number|no\.?|:|=)?\s*(?:\d[ -]?){8,18}\b", text, re.IGNORECASE):
        return True
    for match in re.finditer(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)", text):
        digits = re.sub(r"\D", "", match.group())
        if 13 <= len(digits) <= 19 and luhn_valid(digits):
            return True
    if re.search(r"https?://[^/\s]+@", text, re.IGNORECASE):
        return True
    for match in URL_PATTERN.finditer(text):
        candidate = match.group().rstrip(".,;:!?)]}")
        if candidate.lower().startswith("www."):
            candidate = "https://" + candidate
        try:
            parsed = urlsplit(candidate)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True) + parse_qsl(parsed.fragment, keep_blank_values=True):
                if key.casefold() in SENSITIVE_QUERY_KEYS and value and value != "[REDACTED]":
                    return True
        except ValueError:
            continue
    return False


def _redact_identifiers(text: str) -> str:
    text = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[REDACTED_EMAIL]", text)
    text = re.sub(r"\b[A-Za-z0-9._-]+@[A-Za-z0-9_-]+\b", "[REDACTED_UPI]", text)
    return re.sub(r"(?<!\w)\+?(?:\d[ ()-]?){7,19}(?!\w)", "[REDACTED_NUMBER]", text)


def redact_url(url: str) -> str:
    try:
        parsed = urlsplit(url)
        query = urlencode([(key, "[REDACTED]") for key, _ in parse_qsl(parsed.query, keep_blank_values=True)])
        authority = parsed.hostname or ""
        if ":" in authority:
            authority = f"[{authority}]"
        if parsed.port:
            authority += f":{parsed.port}"
        return urlunsplit((parsed.scheme, authority, _redact_identifiers(parsed.path), query, ""))
    except ValueError:
        return "[REDACTED_URL]"


def redact_text(content: str) -> str:
    def replace_url(match):
        value = match.group().rstrip(".,;:!?)]}")
        if value.lower().startswith("www."):
            value = "https://" + value
        return redact_url(value)

    text = URL_PATTERN.sub(replace_url, content)
    return _redact_identifiers(text)
