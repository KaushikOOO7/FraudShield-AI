import re
from decimal import Decimal, InvalidOperation
from urllib.parse import parse_qsl, urlsplit


def parse_upi_uri(value: str) -> dict:
    parsed = urlsplit(value)
    if parsed.scheme.casefold() != "upi" or parsed.netloc.casefold() != "pay" or parsed.path not in ("", "/") or parsed.fragment:
        raise ValueError("Unsupported UPI URI")
    pairs = parse_qsl(parsed.query, keep_blank_values=True, max_num_fields=30)
    if len({key for key, _ in pairs}) != len(pairs):
        raise ValueError("Duplicate UPI fields")
    fields = dict(pairs)
    payee = fields.get("pa", "")
    if not re.fullmatch(r"[A-Za-z0-9._-]{2,256}@[A-Za-z][A-Za-z0-9]{1,63}", payee):
        raise ValueError("Unsupported payee address syntax")
    currency = fields.get("cu", "INR")
    if currency != "INR":
        raise ValueError("Only INR payment syntax is supported")
    amount = fields.get("am")
    if amount is not None:
        if not re.fullmatch(r"[0-9]{1,8}(?:\.[0-9]{1,2})?", amount):
            raise ValueError("Invalid amount syntax")
        try:
            numeric = Decimal(amount)
            if not numeric.is_finite() or numeric <= 0:
                raise ValueError("Amount must be positive")
        except InvalidOperation:
            raise ValueError("Invalid payment amount") from None
    local, handle = payee.split("@")
    return {
        "payee_hint": local[:2] + "***@" + handle,
        "amount": amount, "currency": currency,
        "validation": "supported_syntax_only",
        "recipient_verified": False,
    }
