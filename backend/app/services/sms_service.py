import asyncio
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from starlette.concurrency import run_in_threadpool

from backend.app.schemas.investigation import EvidenceSource, Finding, InvestigationResponse, Subject
from backend.app.schemas.requests import SMSRequest
from backend.app.services.bundle import InvestigationBundle
from backend.app.services.risk_service import assess_risk
from backend.app.services.sms_rules import sms_rule_findings
from backend.app.utils.privacy import redact_text, redact_url
from backend.app.utils.urls import URLValidationError, extract_urls, parse_public_url


class SMSService:
    def __init__(self, model, urls, settings):
        self.model = model
        self.urls = urls
        self.settings = settings

    async def analyze(self, request: SMSRequest, owner_id: UUID) -> InvestigationBundle:
        created_at = datetime.now(timezone.utc)
        candidates, candidate_count = extract_urls(request.content)
        rule_source, findings = sms_rule_findings(request.content, has_urls=bool(candidates))
        sources = [rule_source]
        limitations = [
            "Sender identity, brand authenticity and community reports were not verified.",
            "This is a historical spam/ham baseline, not validated Indian financial-fraud detection.",
        ]
        model = await run_in_threadpool(self.model.predict, request.content)
        model_source = EvidenceSource(id=uuid4(), name=model.name, kind="model", status=model.status, reference="https://archive.ics.uci.edu/dataset/228/sms+spam+collection", observed_at=model.observed_at)
        model = model.model_copy(update={"source_id": model_source.id})
        sources.append(model_source)
        models = [model]
        limitations.extend(model.limitations)
        if model.status == "available" and model.label == "spam":
            findings.append(Finding(
                id=uuid4(), code="SMS_SPAM_MODEL", description="The trained historical SMS baseline predicts spam. Spam classification is not confirmation of financial fraud.",
                severity="caution", verification_status="model_inference", source_id=model_source.id,
                observed_at=model.observed_at, attributes={"model_version": model.version, "label": model.label},
            ))
        elif model.status != "available":
            limitations.append(f"SMS model inference: {model.status}; no prediction was substituted.")
        normalized = []
        for candidate in candidates:
            try:
                parsed = parse_public_url(candidate)
                if parsed.normalized not in normalized:
                    normalized.append(parsed.normalized)
            except URLValidationError:
                findings.append(Finding(
                    id=uuid4(), code="SMS_UNSUPPORTED_URL", description="A URL-like substring could not be safely validated. It was not fetched or forwarded to providers.",
                    severity="caution", verification_status="documented_rule", source_id=rule_source.id,
                    observed_at=created_at,
                ))
        if candidate_count > 5:
            limitations.append("Only the first five unique URL-like substrings were considered for analysis.")
        inspections = await asyncio.gather(*(self.urls.inspect(url, owner_id, request.use_threat_intelligence) for url in normalized))
        provider_results, parsed_urls, manifests = [], [], {}
        for inspection in inspections:
            findings.extend(inspection.findings)
            sources.extend(inspection.sources)
            models.append(inspection.model)
            limitations.extend(inspection.limitations)
            provider_results.extend(inspection.provider_results)
            parsed_urls.append(inspection.parsed)
            if inspection.model_manifest:
                manifests[inspection.model.name] = inspection.model_manifest
        limitations = list(dict.fromkeys(limitations))
        assessment, actions = assess_risk(findings, models, limitations, "sms", unverified_urls=bool(candidates))
        status = "completed" if all(output.status == "available" for output in models) else "partial"
        if request.use_threat_intelligence and any(outcome.status not in ("matched", "no_match") for _, outcome in provider_results):
            status = "partial"
        response = InvestigationResponse(
            investigation_id=uuid4(), status=status,
            subject=Subject(type="sms", value=redact_text(request.content), attributes={
                "url_count": candidate_count, "analyzed_url_count": len(parsed_urls),
                "urls": [redact_url(url.normalized) for url in parsed_urls],
                "domains": list(dict.fromkeys(url.hostname for url in parsed_urls)),
            }),
            assessment=assessment, findings=findings, sources=sources, models=models,
            limitations=limitations, recommended_actions=actions, created_at=created_at,
            expires_at=created_at + timedelta(days=self.settings.investigation_retention_days),
        )
        return InvestigationBundle(response=response, urls=parsed_urls, provider_results=provider_results, model_manifest=self.model.manifest, model_manifests=manifests)
