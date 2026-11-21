import hashlib
import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from starlette.concurrency import run_in_threadpool

from backend.app.core.errors import APIError
from backend.app.schemas.investigation import EvidenceSource, Finding, InvestigationResponse, Subject
from backend.app.services.bundle import InvestigationBundle
from backend.app.services.qr_decoder import decode_image
from backend.app.services.risk_service import assess_risk
from backend.app.utils.privacy import has_sensitive_values, redact_text
from backend.app.utils.upi import parse_upi_uri
from backend.app.utils.urls import URLValidationError, extract_urls, parse_public_url


class QRService:
    def __init__(self, urls, settings):
        self.urls, self.settings = urls, settings

    async def analyze(self, data: bytes, submission, owner_id):
        decoded = await run_in_threadpool(decode_image, data)
        content = decoded.content
        if content and has_sensitive_values(content):
            raise APIError(422, "sensitive_input", "Remove sensitive credentials from the image before submission")
        now = datetime.now(timezone.utc)
        source = EvidenceSource(id=uuid4(), name="opencv-qr-decoder-v1", kind="rule", status=decoded.status, reference="docs/QR_ANALYSIS.md", observed_at=now)
        findings, sources, models, urls, outcomes, manifests = [], [source], [], [], [], {}
        attributes = {"image_sha256": hashlib.sha256(data).hexdigest(), "image_format": decoded.image_format, "decode_status": decoded.status, "content_type": "unknown"}
        limitations = ["QR decoding does not verify destination safety, recipient identity or fraud.", "No trained QR fraud model is available."]
        if content is None:
            limitations.append("No readable QR payload was found; no content was substituted.")
        else:
            findings.append(Finding(id=uuid4(), code="QR_DECODED", description="One QR payload was decoded from the submitted image. Decoding is not fraud detection.", severity="info", verification_status="documented_rule", source_id=source.id, observed_at=now))
            if content.casefold().startswith("upi:"):
                try:
                    attributes.update(parse_upi_uri(content))
                except ValueError:
                    raise APIError(422, "invalid_upi_uri", "UPI payment URI is outside supported syntax") from None
                attributes["content_type"] = "upi_payment"
                limitations.append("UPI syntax validation does not authenticate a payee. Verify the recipient in your payment application before approving.")
                display = "[REDACTED_UPI_PAYMENT_URI]"
            else:
                candidates, count = extract_urls(content)
                attributes["content_type"] = "url" if content.lower().startswith(("http://", "https://")) else "text"
                attributes["url_count"] = count
                display = redact_text(content)
                normalized_urls = []
                for candidate in candidates:
                    try:
                        normalized = parse_public_url(candidate).normalized
                    except URLValidationError:
                        limitations.append("A decoded URL failed validation and was not forwarded or fetched.")
                        continue
                    if normalized not in normalized_urls:
                        normalized_urls.append(normalized)
                inspections = await asyncio.gather(*(
                    self.urls.inspect(url, owner_id, submission.use_threat_intelligence)
                    for url in normalized_urls
                ))
                for inspection in inspections:
                    urls.append(inspection.parsed)
                    findings.extend(inspection.findings)
                    sources.extend(inspection.sources)
                    models.append(inspection.model)
                    if inspection.model_manifest:
                        manifests[inspection.model.name] = inspection.model_manifest
                    outcomes.extend(inspection.provider_results)
                    limitations.extend(inspection.limitations)
                if count > 5:
                    limitations.append("Only the first five extracted URL candidates were considered.")
        if content is None:
            display = None
        if display is not None and len(display) > 5000:
            raise APIError(422, "payload_too_large", "Redacted QR content exceeds the investigation size limit")
        limitations = list(dict.fromkeys(limitations))
        assessment, actions = assess_risk(findings, models, limitations, "qr", unverified_urls=bool(urls))
        if attributes["content_type"] == "upi_payment":
            actions.insert(0, "Confirm the recipient and payment amount in your UPI application before approving payment; a QR code does not require entering a PIN to receive money.")
        response = InvestigationResponse(
            investigation_id=uuid4(), status="partial", subject=Subject(type="qr", value=display, attributes=attributes),
            assessment=assessment, findings=findings, sources=sources, models=models,
            limitations=limitations, recommended_actions=actions, created_at=now,
            expires_at=now + timedelta(days=self.settings.investigation_retention_days),
        )
        return InvestigationBundle(response=response, urls=urls, provider_results=outcomes, model_manifests=manifests, qr_analysis={"content_type": attributes["content_type"], "redacted_content": display or "", "decoded_attributes": attributes})
