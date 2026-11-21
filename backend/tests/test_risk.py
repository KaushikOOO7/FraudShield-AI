"""Isolated non-production rule/evidence fixtures; no fabricated production incidents."""
from datetime import datetime, timezone
from uuid import uuid4

from backend.app.schemas.investigation import Finding, ModelResult
from backend.app.services.risk_service import assess_risk
from backend.app.services.sms_rules import sms_rule_findings


def model(label, status="available"):
    return ModelResult(name="ISOLATED_TEST_MODEL_OUTPUT", version="test-only-version" if status == "available" else None, task="sms_spam_detection", status=status, label=label, observed_at=datetime.now(timezone.utc))


def test_model_prediction_alone_never_confirms_fraud():
    assessment, _ = assess_risk([], [model("spam")], [], "sms")
    assert assessment.classification == "EXERCISE_CAUTION"
    assert assessment.risk_score is None
    assert assessment.confidence is None


def test_no_model_and_no_evidence_is_insufficient():
    assessment, _ = assess_risk([], [model(None, "model_not_trained")], ["No trained model"], "sms")
    assert assessment.classification == "EXERCISE_CAUTION"
    assert "insufficient" in assessment.explanation


def test_ham_with_unverified_url_does_not_imply_safe():
    assessment, _ = assess_risk([], [model("ham")], ["Destination unverified"], "sms", unverified_urls=True)
    assert assessment.classification == "EXERCISE_CAUTION"


def test_ham_is_only_limited_safe_indicators():
    assessment, _ = assess_risk([], [model("ham")], ["Sender unverified"], "sms")
    assert assessment.classification == "SAFE_INDICATORS"
    assert "do not" in assessment.explanation


def test_validated_provider_warning_is_high_risk_not_confirmed():
    finding = Finding(id=uuid4(), code="ISOLATED_PROVIDER_CONTRACT_FIXTURE", description="Synthetic provider fixture only", severity="high", verification_status="provider_report", source_id=uuid4(), observed_at=datetime.now(timezone.utc))
    assessment, _ = assess_risk([finding], [model("ham")], [], "sms")
    assert assessment.classification == "HIGH_RISK"
    assert assessment.risk_score is None


def test_secret_request_with_kyc_pressure_combines_actual_patterns():
    # Explicit fictional validation string; it never enters a production database.
    _, findings = sms_rule_findings("ISOLATED TEST: share your OTP; urgent KYC blocked. https://example.com/", has_urls=True)
    assert {finding.code for finding in findings} == {"SMS_REQUESTS_SECRET", "SMS_KYC_PRESSURE_LINK"}
    assessment, actions = assess_risk(findings, [], [], "sms", unverified_urls=True)
    assert assessment.classification == "HIGH_RISK"
    assert any("Never disclose" in action for action in actions)


def test_negated_secret_warning_is_not_a_solicitation():
    for content in ("Never share your OTP", "Do not share your PIN", "Don't send your password", "You should not to reveal your OTP"):
        _, findings = sms_rule_findings(content, has_urls=False)
        assert not any(finding.code == "SMS_REQUESTS_SECRET" for finding in findings)
