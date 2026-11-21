from datetime import datetime, timedelta, timezone
from uuid import uuid4

from backend.app.schemas.investigation import EvidenceSource, Finding, InvestigationResponse, Subject
from backend.app.services.bundle import InvestigationBundle
from backend.app.services.risk_service import assess_risk
from backend.app.utils.indicators import normalized_indicator


class CallerService:
    def __init__(self, settings):
        self.settings = settings

    async def analyze(self, submission, owner_id):
        now = datetime.now(timezone.utc)
        masked, _ = normalized_indicator("phone", submission.phone_number)
        source = EvidenceSource(id=uuid4(), name="phone-format-rules-v1", kind="rule", status="completed", reference="docs/CALLER_ANALYSIS.md", observed_at=now)
        findings = [Finding(id=uuid4(), code="PHONE_FORMAT_ACCEPTED", description="The submitted number matches supported E.164/Indian mobile syntax. Syntax does not authenticate a caller or establish reputation.", severity="info", verification_status="documented_rule", source_id=source.id, observed_at=now)]
        reputation = EvidenceSource(id=uuid4(), name="caller-reputation", kind="threat_intelligence", status="provider_not_configured", reference="docs/CALLER_ANALYSIS.md", observed_at=now)
        limitations = ["No permitted caller-reputation provider is configured; no lookup was performed.", "Caller identity and number ownership are unverified; caller IDs may be spoofed.", "No caller-fraud dataset or trained model is available.", "Unreviewed user reports are not verified reputation evidence.", "Only a masked phone display is stored; no plaintext phone index is created."]
        assessment, actions = assess_risk(findings, [], limitations, "caller")
        result = InvestigationResponse(investigation_id=uuid4(), status="partial", subject=Subject(type="caller", value=masked, attributes={"format": "supported_e164_syntax", "identity_verified": False}), assessment=assessment, findings=findings, sources=[source, reputation], models=[], limitations=limitations, recommended_actions=actions, created_at=now, expires_at=now + timedelta(days=self.settings.investigation_retention_days))
        return InvestigationBundle(response=result)
