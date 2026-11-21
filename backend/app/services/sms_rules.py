import re
from datetime import datetime, timezone
from uuid import uuid4

from backend.app.schemas.investigation import EvidenceSource, Finding

RULE_REFERENCE = "docs/RISK_METHODOLOGY.md"


def sms_rule_findings(content: str, has_urls: bool) -> tuple[EvidenceSource, list[Finding]]:
    now = datetime.now(timezone.utc)
    source = EvidenceSource(id=uuid4(), name="sms-rules-v1", kind="rule", status="completed", reference=RULE_REFERENCE, observed_at=now)
    findings = []

    def add(code, description):
        findings.append(Finding(id=uuid4(), code=code, description=description, severity="caution", verification_status="documented_rule", source_id=source.id, observed_at=now))

    text = content.casefold()
    for match in re.finditer(r"\b(?:send|share|provide|tell|disclose|reveal)\b(?:\W+\w+){0,4}\W+\b(?:otp|pin|password|passcode|cvv|cvc)\b", text):
        preceding = text[max(0, match.start() - 30):match.start()]
        if not re.search(r"(?:do not|don't|never|not to)\s+(?:\w+\s+){0,2}$", preceding):
            add("SMS_REQUESTS_SECRET", "The message asks the recipient to disclose an authentication secret. This is an observed text pattern, not verified sender intent.")
            break
    if has_urls and re.search(r"\b(?:kyc|know your customer)\b", text) and re.search(r"\b(?:urgent|immediately|blocked|suspended|suspend|expired|deactivated)\b", text):
        add("SMS_KYC_PRESSURE_LINK", "The message combines KYC language, account or time pressure, and a URL. This heuristic does not establish whether the bank or request is genuine.")
    if "digital arrest" in text:
        add("SMS_DIGITAL_ARREST_LANGUAGE", "The message contains the phrase 'digital arrest'. Independent verification is required; the sender and incident have not been verified.")
    if re.search(r"\b(?:pay|payment|transfer|deposit)\b", text) and re.search(r"\b(?:arrest|jail|warrant|police)\b", text):
        add("SMS_PAYMENT_THREAT", "The message mentions both payment and arrest or police-related language. Context and sender authority are unverified.")
    return source, findings
