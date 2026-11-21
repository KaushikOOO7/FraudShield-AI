import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from starlette.concurrency import run_in_threadpool

from backend.app.core.config import PROJECT_ROOT
from backend.app.core.errors import APIError
from backend.app.schemas.investigation import EvidenceSource, Finding, InvestigationResponse, Subject
from backend.app.schemas.apk import APKWorkerResult
from backend.app.services.bundle import InvestigationBundle
from backend.app.services.risk_service import assess_risk
from backend.app.utils.privacy import redact_text
from backend.app.utils.urls import URLValidationError, parse_public_url


def parser_available():
    return importlib.util.find_spec("androguard") is not None


def validate_apk_archive(data):
    if not data.startswith(b"PK\x03\x04"):
        raise APIError(422, "invalid_apk", "APK must be an Android ZIP archive")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > 5000 or "AndroidManifest.xml" not in archive.namelist():
                raise ValueError
            if len({entry.filename for entry in entries}) != len(entries):
                raise ValueError
            total = 0
            for entry in entries:
                if entry.filename.startswith("/") or "\\" in entry.filename or ".." in entry.filename.split("/") or entry.flag_bits & 1:
                    raise ValueError
                if entry.file_size > 40 * 1024 * 1024 or entry.file_size / max(1, entry.compress_size) > 100:
                    raise ValueError
                total += entry.file_size
            if total > 128 * 1024 * 1024:
                raise ValueError
    except (zipfile.BadZipFile, ValueError):
        raise APIError(422, "invalid_apk_archive", "APK archive exceeds supported structural or expansion limits") from None


def parse_apk(data):
    validate_apk_archive(data)
    if not parser_available():
        raise APIError(503, "apk_parser_unavailable", "Androguard static analysis is not installed")
    with tempfile.TemporaryDirectory(prefix="fraudshield-apk-") as directory:
        path = Path(directory) / "upload.apk"
        path.write_bytes(data)
        path.chmod(0o600)
        try:
            process = subprocess.run([sys.executable, "-m", "backend.app.services.apk_worker", str(path)], cwd=PROJECT_ROOT, env={"PATH": os.defpath, "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=15)
            if process.returncode != 0 or len(process.stdout) > 65536:
                raise APIError(422, "apk_processing_failed", "APK parsing exceeded supported resource limits")
            result = APKWorkerResult.model_validate(json.loads(process.stdout))
            if result.status == "parser_unavailable":
                raise APIError(503, "apk_parser_unavailable", "APK parser dependencies are unavailable")
            if result.status != "parsed" or result.metadata is None:
                raise APIError(422, "invalid_apk", "APK metadata could not be validated")
            return result.metadata.model_dump(mode="json")
        except subprocess.TimeoutExpired:
            raise APIError(422, "apk_processing_timeout", "APK parsing timed out") from None
        except (ValueError, OSError):
            raise APIError(422, "apk_processing_failed", "APK parsing failed") from None


class APKService:
    def __init__(self, settings):
        self.settings = settings

    async def analyze(self, data, submission, owner_id):
        metadata = await run_in_threadpool(parse_apk, data)
        digest = hashlib.sha256(data).hexdigest()
        now = datetime.now(timezone.utc)
        source = EvidenceSource(id=uuid4(), name="androguard-static-v1", kind="rule", status="completed", reference="docs/APK_ANALYSIS.md", observed_at=now, details={"parser_version": metadata["parser_version"]})
        candidates = metadata.pop("embedded_url_candidates", [])
        safe_urls = []
        for candidate in candidates:
            try:
                safe_urls.append(parse_public_url(candidate))
            except URLValidationError:
                continue
        metadata["embedded_urls"] = [redact_text(url.normalized) for url in safe_urls]
        for key in ("application_name", "package_name", "version_name"):
            if isinstance(metadata.get(key), str):
                metadata[key] = redact_text(metadata[key])
        findings = [Finding(id=uuid4(), code="APK_STATIC_METADATA", description="Static APK metadata and SHA-256 were extracted without installing or executing the application.", severity="info", verification_status="documented_rule", source_id=source.id, observed_at=now, attributes={"sha256": digest, "package_name": metadata.get("package_name")})]
        permissions = set(metadata["requested_permissions"])
        sms = permissions & {"android.permission.READ_SMS", "android.permission.RECEIVE_SMS", "android.permission.SEND_SMS"}
        if sms and "android.permission.READ_CONTACTS" in permissions:
            findings.append(Finding(id=uuid4(), code="APK_SMS_CONTACT_PERMISSIONS", description="The manifest requests SMS and contacts access. Confirm that these declarations are necessary for the application's purpose; they are not proof of malware or granted access.", severity="caution", verification_status="documented_rule", source_id=source.id, observed_at=now, attributes={"requested_permissions": sorted(sms | {"android.permission.READ_CONTACTS"})}))
        limitations = ["Static analysis does not prove an APK safe or malicious; no APK was installed or executed.", "No trained APK fraud model, dynamic analysis or configured malicious-hash lookup is available.", "Only explicit exported=true declarations are listed; effective platform/version defaults are not inferred.", "Embedded URL scanning covers the first 2 MiB of each DEX and at most 20 candidates; no absence-of-threat conclusion is made.", "Signing certificate metadata does not authenticate publisher identity or verify the complete APK signature scheme."]
        assessment, actions = assess_risk(findings, [], limitations, "apk", unverified_urls=bool(safe_urls))
        result = InvestigationResponse(investigation_id=uuid4(), status="partial", subject=Subject(type="apk", value=digest, attributes=metadata), assessment=assessment, findings=findings, sources=[source], models=[], limitations=limitations, recommended_actions=actions, created_at=now, expires_at=now + timedelta(days=self.settings.investigation_retention_days))
        return InvestigationBundle(response=result, urls=safe_urls, apk_analysis={"sha256": digest, "static_metadata": metadata})
