from backend.app.schemas.investigation import Assessment, Finding, ModelResult

METHODOLOGY_VERSION = "evidence-qualitative-v1"


def assess_risk(
    findings: list[Finding], models: list[ModelResult], missing_information: list[str],
    subject_type: str, unverified_urls: bool = False,
) -> tuple[Assessment, list[str]]:
    """Qualitative rules only. No probability conversion and no confirmed-fraud path."""
    codes = {finding.code for finding in findings}
    provider_high = any(
        finding.verification_status == "provider_report" and finding.severity == "high"
        for finding in findings
    )
    secret_pressure = "SMS_REQUESTS_SECRET" in codes and bool(
        codes & {"SMS_KYC_PRESSURE_LINK", "SMS_PAYMENT_THREAT"}
    )
    warnings = any(finding.severity in ("caution", "high") for finding in findings)
    spam = any(model.status == "available" and model.label == "spam" for model in models)
    ham = any(model.status == "available" and model.label == "ham" for model in models)
    if provider_high:
        classification = "HIGH_RISK"
        explanation = "A configured provider returned validated threat indicators. Treat this as high risk; it is not human-reviewed confirmation of fraud."
    elif secret_pressure:
        classification = "HIGH_RISK"
        explanation = "The message combines a request to disclose authentication secrets with account or payment pressure. This documented rule combination warrants high risk handling; it is not proof of fraud."
    elif warnings or spam:
        classification = "EXERCISE_CAUTION"
        explanation = "Documented rules or the historical spam model identified warning indicators. Verify the subject independently before acting."
    elif subject_type == "sms" and ham and not unverified_urls:
        classification = "SAFE_INDICATORS"
        explanation = "The historical SMS model predicts ham and no implemented rule raised a warning. These limited safe indicators do not verify the sender or guarantee safety."
    else:
        classification = "EXERCISE_CAUTION"
        explanation = "There is insufficient evidence to verify legitimacy. Unavailable capabilities and missing information are listed."
    assessment = Assessment(
        classification=classification, risk_score=None, score_type=None, explanation=explanation,
        methodology_version=METHODOLOGY_VERSION, confidence=None,
        missing_information=list(dict.fromkeys(missing_information)),
    )
    actions = ["Verify the sender or destination through an independently obtained official contact before acting."]
    if "SMS_REQUESTS_SECRET" in codes:
        actions.append("Never disclose OTPs, passwords, card credentials or a UPI PIN to someone who contacts you.")
    if classification == "HIGH_RISK":
        actions.insert(0, "Avoid opening links, making payments or installing applications associated with this submission while you verify it.")
    if "SMS_DIGITAL_ARREST_LANGUAGE" in codes or "SMS_PAYMENT_THREAT" in codes:
        actions.append("Independently contact the relevant authority and your bank if a message pressures you to pay under a threat of arrest.")
    if classification == "EXERCISE_CAUTION":
        actions.append("Treat missing provider information and a no-match lookup as uncertainty, not approval to proceed.")
    return assessment, actions
