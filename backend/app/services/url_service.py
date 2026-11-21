from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from starlette.concurrency import run_in_threadpool
from backend.app.ml.inference.urls import URLInference

from backend.app.intelligence.base import ProviderOutcome
from backend.app.schemas.investigation import EvidenceSource, Finding, InvestigationResponse, ModelResult, Subject
from backend.app.schemas.requests import URLRequest
from backend.app.services.bundle import InvestigationBundle
from backend.app.services.risk_service import assess_risk
from backend.app.utils.privacy import redact_url
from backend.app.utils.urls import ParsedURL, parse_public_url


@dataclass
class URLInspection:
    parsed: ParsedURL
    findings: list[Finding]
    sources: list[EvidenceSource]
    model: ModelResult
    limitations: list[str]
    provider_results: list[tuple[UUID, ProviderOutcome]]
    model_manifest: dict | None = None


class URLService:
    def __init__(self, intelligence, settings):
        self.intelligence = intelligence
        self.settings = settings
        self.model = URLInference(settings.url_model_dir)

    async def inspect(self, url: str, owner_id: UUID, use_intelligence: bool) -> URLInspection:
        parsed = parse_public_url(url)
        now = datetime.now(timezone.utc)
        rule_source = EvidenceSource(id=uuid4(), name="url-structure-rules-v1", kind="rule", status="completed", reference="docs/RISK_METHODOLOGY.md", observed_at=now)
        findings = []

        def add(code, description, severity="caution", attributes=None):
            findings.append(Finding(id=uuid4(), code=code, description=description, severity=severity, verification_status="documented_rule", source_id=rule_source.id, observed_at=now, attributes=attributes or {}))

        if parsed.ip_literal:
            add("URL_IP_LITERAL", "The URL uses a public IP address instead of a domain name. This structural indicator does not prove phishing.")
        if parsed.scheme == "http":
            add("URL_HTTP_SCHEME", "The URL uses HTTP. Transport encryption and destination legitimacy have not been verified.", severity="info")
        if "xn--" in parsed.hostname:
            add("URL_INTERNATIONAL_DOMAIN", "The URL contains an internationalized domain. Unicode spelling may need independent verification; this alone is not an impersonation finding.", severity="info")
        if len(parsed.normalized) >= 200:
            add("URL_LONG_STRUCTURE", "The URL is at least 200 characters long. Long URLs are a weak structural indicator and may be legitimate.", attributes={"length": len(parsed.normalized)})
        if not parsed.ip_literal and len(parsed.hostname.split(".")) >= 6:
            add("URL_MANY_HOST_LABELS", "The hostname contains at least six labels. Complex hostnames can be legitimate; ownership is unverified.")
        model = await run_in_threadpool(self.model.predict, parsed.normalized)
        model_source = EvidenceSource(id=uuid4(), name=model.name, kind="model", status=model.status, reference="docs/DATASET_REGISTER.md", observed_at=model.observed_at)
        model = model.model_copy(update={"source_id": model_source.id})
        if model.status == "available" and model.label == "phishing":
            add("URL_PHISHING_MODEL", "The trained historical raw-URL classifier predicts phishing. This model prediction does not confirm fraud.")
            findings[-1] = findings[-1].model_copy(update={"source_id": model_source.id, "verification_status": "model_inference", "attributes": {"model_version": model.version}})
        sources = [rule_source, model_source]
        limitations = [
            *model.limitations,
            "Redirects and destination pages were not fetched.",
            "Domain registration age, ownership, certificate and brand authenticity were not verified.",
            "HTTPS spelling and a provider no-match are not guarantees of safety.",
        ]
        outcomes = await self.intelligence.lookup_url(parsed.normalized, owner_id, requested=use_intelligence)
        provider_results = []
        provider_references = {provider.name: provider.reference for provider in self.intelligence.providers}
        for outcome in outcomes:
            if outcome.provider == "google_safe_browsing" and outcome.valid_until and outcome.valid_until <= datetime.now(timezone.utc):
                outcome = outcome.model_copy(update={"status": "stale"})
            source = EvidenceSource(
                id=uuid4(), name=outcome.provider, kind="threat_intelligence", status=outcome.status,
                reference=provider_references[outcome.provider], observed_at=outcome.checked_at,
                details={
                    "verdict": outcome.verdict, "cached": outcome.cached,
                    "report_at": outcome.report_at.isoformat() if outcome.report_at else None,
                    "detector_counts": outcome.detector_counts, "threat_categories": outcome.threat_categories,
                    "retry_after_seconds": outcome.retry_after_seconds,
                    "provider_details": outcome.details,
                    "valid_until": outcome.valid_until.isoformat() if outcome.valid_until else None,
                    "attribution": "Advisory provided by Google" if outcome.provider == "google_safe_browsing" and outcome.verdict else None,
                    "advisory_url": "https://developers.google.com/safe-browsing/v4/advisory" if outcome.provider == "google_safe_browsing" and outcome.verdict else None,
                },
            )
            sources.append(source)
            provider_results.append((source.id, outcome))
            if outcome.provider in ("urlhaus", "phishtank", "abuseipdb") and outcome.verdict in ("malicious_indicators", "suspicious_indicators"):
                severity = "high" if outcome.status == "matched" and outcome.provider != "abuseipdb" else "caution"
                findings.append(Finding(
                    id=uuid4(), code="THREAT_PROVIDER_REPORT", description=f"{outcome.provider} returned validated threat indicators for its documented scope. This is a provider report, not confirmation of fraud.",
                    severity=severity, verification_status="provider_report", source_id=source.id,
                    observed_at=outcome.checked_at, attributes={"provider": outcome.provider, "url": redact_url(parsed.normalized), "categories": outcome.threat_categories, **outcome.details},
                ))
            if outcome.provider == "google_safe_browsing" and outcome.status == "matched":
                findings.append(Finding(
                    id=uuid4(), code="SAFE_BROWSING_THREAT_MATCH", description="Google Safe Browsing reports a potentially unsafe destination. Advisory provided by Google. This is a provider warning with possible false positives, not human-reviewed confirmation of fraud.",
                    severity="high", verification_status="provider_report", source_id=source.id,
                    observed_at=outcome.checked_at, attributes={"categories": outcome.threat_categories, "url": redact_url(parsed.normalized)},
                ))
            if outcome.provider == "virustotal" and outcome.verdict in ("malicious_indicators", "suspicious_indicators"):
                counts = outcome.detector_counts
                severity = "high" if outcome.status == "matched" and counts.get("malicious", 0) >= 3 else "caution"
                findings.append(Finding(
                    id=uuid4(), code="VIRUSTOTAL_DETECTOR_REPORT",
                    description=f"VirusTotal's last analysis reports {counts.get('malicious', 0)} malicious and {counts.get('suspicious', 0)} suspicious detector votes. Detector votes are not proof of fraud.",
                    severity=severity, verification_status="provider_report", source_id=source.id,
                    observed_at=outcome.checked_at, attributes={"detector_counts": counts, "report_at": outcome.report_at.isoformat() if outcome.report_at else None, "url": redact_url(parsed.normalized)},
                ))
            if outcome.status not in ("matched", "no_match"):
                limitations.append(f"{outcome.provider}: {outcome.status}; no current validated reputation verdict.")
            limitations.extend(outcome.limitations)
        return URLInspection(parsed, findings, sources, model, list(dict.fromkeys(limitations)), provider_results, self.model.manifest)

    async def analyze(self, request: URLRequest, owner_id: UUID) -> InvestigationBundle:
        created_at = datetime.now(timezone.utc)
        inspection = await self.inspect(request.url, owner_id, request.use_threat_intelligence)
        assessment, actions = assess_risk(inspection.findings, [inspection.model], inspection.limitations, "url", unverified_urls=True)
        response = InvestigationResponse(
            investigation_id=uuid4(), status="partial",
            subject=Subject(type="url", value=redact_url(inspection.parsed.normalized), attributes={
                "domain": inspection.parsed.hostname, "scheme": inspection.parsed.scheme,
                "ip_literal": inspection.parsed.ip_literal, "uses_https_scheme": inspection.parsed.scheme == "https",
                "url_length": len(inspection.parsed.normalized),
            }),
            assessment=assessment, findings=inspection.findings, sources=inspection.sources,
            models=[inspection.model], limitations=inspection.limitations, recommended_actions=actions,
            created_at=created_at, expires_at=created_at + timedelta(days=self.settings.investigation_retention_days),
        )
        return InvestigationBundle(response=response, urls=[inspection.parsed], provider_results=inspection.provider_results, model_manifests={inspection.model.name: inspection.model_manifest} if inspection.model_manifest else {})
