"""Actual SQL constraints in isolated SQLite databases; not a PostgreSQL RLS claim."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.config import Settings
from backend.app.core.errors import APIError
from backend.app.core.security import Principal
from backend.app.database.connection import Database
from backend.app.database.migrate import MigrationError, apply_migrations
from backend.app.database.models import (
    Base, Evidence, EvidenceSource, GraphEdge, Investigation, InvestigationEvent,
    RiskAssessment, User,
)


@pytest.fixture
def database(tmp_path):
    settings = Settings(app_env="test", database_url=f"sqlite:///{tmp_path / 'test.sqlite3'}", _env_file=None)
    database = Database(settings)
    apply_migrations(database.engine)
    yield database
    database.dispose()


def investigation(owner):
    # Explicit isolated test-only record, never written to application storage.
    return Investigation(
        id=uuid4(), owner_id=owner, subject_type="sms", source="api",
        subject_value="ISOLATED NON-PRODUCTION STORAGE FIXTURE",
        status="completed", result={}, expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )


def test_migrations_connectivity_and_no_seeded_data(database):
    assert database.status() == {"dialect": "sqlite", "status": "connected"}
    assert apply_migrations(database.engine) == []
    with database.engine.connect() as connection:
        assert connection.execute(select(User)).all() == []
        assert connection.execute(select(Investigation)).all() == []
        actual = inspect(connection)
        assert set(Base.metadata.tables).issubset(actual.get_table_names())
        for table in Base.metadata.tables.values():
            assert {column.name for column in table.columns} == {column["name"] for column in actual.get_columns(table.name)}
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1


def test_missing_migrations_is_explicit(tmp_path):
    database = Database(Settings(database_url=f"sqlite:///{tmp_path / 'unmigrated.sqlite3'}", _env_file=None))
    try:
        assert database.status()["status"] == "migrations_required"
        with pytest.raises(APIError) as error:
            database.ensure_ready()
        assert error.value.status_code == 503
    finally:
        database.dispose()


def test_edited_migration_rejected(database, tmp_path):
    from backend.app.database.migrate import MIGRATIONS_ROOT
    target = tmp_path / "migrations" / "sqlite"
    target.mkdir(parents=True)
    for migration in (MIGRATIONS_ROOT / "sqlite").glob("*.sql"):
        (target / migration.name).write_bytes(migration.read_bytes())
    original = (MIGRATIONS_ROOT / "sqlite/0001_core.sql").read_text()
    (target / "0001_core.sql").write_text(original + "\n-- changed test-only copy\n")
    with pytest.raises(MigrationError, match="edited"):
        apply_migrations(database.engine, tmp_path / "migrations")


def test_owner_foreign_key_prevents_cross_tenant_evidence(database):
    owner_a, owner_b = uuid4(), uuid4()
    case = investigation(owner_a)
    case_id = case.id
    with Session(database.engine) as session, session.begin():
        session.add_all([User(id=owner_a), User(id=owner_b)])
        session.flush()
        session.add(case)
    with Session(database.engine) as session:
        session.add(InvestigationEvent(owner_id=owner_b, investigation_id=case_id, event_type="isolated_fixture", details={}))
        with pytest.raises(IntegrityError):
            session.commit()


def test_delete_cascades_evidence_sources_events_and_risk(database):
    owner = uuid4()
    case = investigation(owner)
    case_id = case.id
    source_id = uuid4()
    with Session(database.engine) as session, session.begin():
        session.add(User(id=owner))
        session.flush()
        session.add(case)
        session.flush()
        session.add(EvidenceSource(
            id=source_id, owner_id=owner, investigation_id=case.id, name="isolated-test-rule",
            kind="rule", status="completed", observed_at=datetime.now(timezone.utc),
        ))
        session.flush()
        session.add(Evidence(
            owner_id=owner, investigation_id=case.id, source_id=source_id,
            code="ISOLATED_TEST_ONLY", description="Non-production constraint fixture", severity="info",
            verification_status="documented_rule", observed_at=datetime.now(timezone.utc), attributes={},
        ))
        session.add(InvestigationEvent(owner_id=owner, investigation_id=case.id, event_type="completed", details={}))
        session.add(RiskAssessment(
            owner_id=owner, investigation_id=case.id, classification="EXERCISE_CAUTION",
            risk_score=None, score_type=None, explanation="Isolated test only",
            methodology_version="test", missing_information=[],
        ))
    with Session(database.engine) as session, session.begin():
        session.delete(session.get(Investigation, case_id))
    with Session(database.engine) as session:
        for model in (Investigation, Evidence, EvidenceSource, InvestigationEvent, RiskAssessment):
            assert session.execute(select(model)).all() == []


def test_confirmed_fraud_requires_authority_and_human_review(database):
    owner = uuid4()
    case = investigation(owner)
    case_id = case.id
    with Session(database.engine) as session, session.begin():
        session.add(User(id=owner))
        session.flush()
        session.add(case)
    with Session(database.engine) as session:
        session.add(RiskAssessment(
            owner_id=owner, investigation_id=case_id, classification="CONFIRMED_FRAUD",
            explanation="Isolated negative fixture", methodology_version="test", missing_information=[],
        ))
        with pytest.raises(IntegrityError):
            session.commit()


def test_shared_database_request_quota_is_enforced(database):
    database.settings.rate_limit_per_minute = 1
    principal = Principal(user_id=uuid4())
    with database.owned_session(principal):
        pass
    with pytest.raises(APIError) as error:
        with database.owned_session(principal):
            pass
    assert error.value.status_code == 429
    assert int(error.value.headers["Retry-After"]) > 0
