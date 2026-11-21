"""Explicit, ordered, checksum-checked SQL migrations; no startup schema mutation."""
import hashlib
from pathlib import Path

from sqlalchemy import Column, DateTime, MetaData, String, Table, func, select

from backend.app.core.config import PROJECT_ROOT, get_settings

MIGRATIONS_ROOT = PROJECT_ROOT / "backend/migrations"
STATEMENT_SEPARATOR = "-- statement-breakpoint"
schema_migrations = Table(
    "schema_migrations", MetaData(),
    Column("version", String(100), primary_key=True),
    Column("checksum", String(64), nullable=False),
    Column("applied_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)


class MigrationError(RuntimeError):
    pass


def migration_files(dialect: str, root: Path = MIGRATIONS_ROOT) -> list[Path]:
    paths = sorted((root / dialect).glob("*.sql"))
    if not paths:
        raise MigrationError("No migrations exist for this database dialect")
    return paths


def expected_migrations(dialect: str, root: Path = MIGRATIONS_ROOT) -> dict[str, str]:
    return {path.stem: hashlib.sha256(path.read_bytes()).hexdigest() for path in migration_files(dialect, root)}


def apply_migrations(engine, root: Path = MIGRATIONS_ROOT) -> list[str]:
    paths = migration_files(engine.dialect.name, root)
    applied_now = []
    with engine.connect() as connection:
        try:
            if engine.dialect.name == "sqlite":
                connection.exec_driver_sql("BEGIN IMMEDIATE")
            else:
                connection.exec_driver_sql("SELECT pg_advisory_xact_lock(719774680)")
            schema_migrations.create(connection, checkfirst=True)
            existing = dict(connection.execute(select(schema_migrations.c.version, schema_migrations.c.checksum)).all())
            expected = expected_migrations(engine.dialect.name, root)
            if set(existing) - set(expected):
                raise MigrationError("Database has migrations unknown to this application version")
            for path in paths:
                version = path.stem
                checksum = expected[version]
                if version in existing:
                    if existing[version] != checksum:
                        raise MigrationError("An applied migration was edited; restore it and create a new revision")
                    continue
                for statement in path.read_text().split(STATEMENT_SEPARATOR):
                    if statement.strip():
                        connection.exec_driver_sql(statement.strip())
                connection.execute(schema_migrations.insert().values(version=version, checksum=checksum))
                applied_now.append(version)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    return applied_now


def main():
    from backend.app.database.connection import Database

    database = Database(get_settings(), migration_mode=True)
    if database.engine is None:
        raise SystemExit("PostgreSQL driver unavailable; install backend/requirements-postgres.txt")
    try:
        revisions = apply_migrations(database.engine)
        print("Applied migrations:", ", ".join(revisions) if revisions else "already up to date")
    except Exception as exc:
        # Connection/driver exception strings can expose credential-bearing URLs.
        if isinstance(exc, MigrationError):
            raise SystemExit(str(exc)) from None
        raise SystemExit(f"Migration failed ({type(exc).__name__}); check database access and configuration") from None
    finally:
        database.dispose()


if __name__ == "__main__":
    main()
