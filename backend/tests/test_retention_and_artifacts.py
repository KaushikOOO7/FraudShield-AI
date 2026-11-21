import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
import pytest

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.config import PROJECT_ROOT, Settings
from backend.app.database.connection import Database
from backend.app.database.migrate import apply_migrations
from backend.app.database.models import AuditLog, Investigation, User
from backend.app.database.retention import purge_expired
from scripts.prepare_sms_web_export import prepare


def test_retention_deletes_only_expired_records_and_old_audits(tmp_path):
    # Test-only storage records, kept in a disposable temporary database.
    now = datetime.now(timezone.utc)
    database = Database(Settings(database_url=f"sqlite:///{tmp_path / 'retention.sqlite3'}", _env_file=None))
    apply_migrations(database.engine)
    owner = uuid4()
    with Session(database.engine) as session, session.begin():
        session.add(User(id=owner))
        session.flush()
        for expiry in (now - timedelta(days=1), now + timedelta(days=1)):
            session.add(Investigation(
                owner_id=owner, subject_type="sms", source="api", subject_value="ISOLATED RETENTION FIXTURE",
                status="completed", result={}, expires_at=expiry,
            ))
        for created in (now - timedelta(days=181), now):
            session.add(AuditLog(owner_id=owner, action="ISOLATED_TEST_ONLY", request_id=uuid4(), created_at=created))
    result = purge_expired(database, now)
    assert result["investigations_deleted"] == 1
    assert result["audit_logs_deleted"] == 1
    with Session(database.engine) as session:
        assert session.scalar(select(func.count()).select_from(Investigation)) == 1
        assert session.scalar(select(func.count()).select_from(AuditLog)) == 1
    database.dispose()


def test_genuine_web_export_reproduces_registered_bytes(tmp_path):
    source = PROJECT_ROOT / "data/raw/uci_sms_web_export.json"
    if not source.exists():
        # An official-download CI run may have no web export; do not fabricate one.
        pytest.skip("Official-download CI has no browser export; no substitute is generated")
    output = tmp_path / "prepared.jsonl"
    result = prepare(source, output)
    actual = json.loads((PROJECT_ROOT / "backend/app/ml/models/sms_manifest.json").read_text())["dataset"]
    assert result["file_sha256"] == actual["file_sha256"]
    assert result["record_count"] == 5574
    assert result["byte_identical_to_original"] is False
    assert result["acquired_at"] == "2026-11-21"
