import hashlib
import json
import math
import time
from contextlib import contextmanager
from pathlib import Path

from fastapi import Depends, Request
from sqlalchemy import case, create_engine, event, func, inspect, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.core.config import Settings
from backend.app.core.errors import APIError
from backend.app.core.security import Principal, current_principal
from backend.app.database.migrate import expected_migrations, schema_migrations
from backend.app.database.models import APIRateLimitBucket, User


class Database:
    def __init__(self, settings: Settings, migration_mode: bool = False):
        self.settings = settings
        self.engine = None
        self.migration_mode = migration_mode
        self._schema_verified = False
        url = make_url(settings.database_url.get_secret_value())
        self.dialect = url.get_backend_name()
        try:
            if self.dialect == "sqlite":
                if url.database and url.database != ":memory:":
                    Path(url.database).parent.mkdir(parents=True, exist_ok=True)
                options = {"connect_args": {"check_same_thread": False, "timeout": 5}}
                if url.database == ":memory:":
                    options["poolclass"] = StaticPool
                self.engine = create_engine(url, **options)

                @event.listens_for(self.engine, "connect")
                def enforce_foreign_keys(connection, record):
                    cursor = connection.cursor()
                    cursor.execute("PRAGMA foreign_keys=ON")
                    cursor.execute("PRAGMA busy_timeout=5000")
                    cursor.close()
            else:
                self.engine = create_engine(
                    url, pool_pre_ping=True, pool_size=5, max_overflow=5, pool_timeout=5,
                    connect_args={
                        "connect_timeout": 5, "prepare_threshold": None,
                        "options": "-c statement_timeout=5000 -c idle_in_transaction_session_timeout=10000",
                    },
                )
        except ModuleNotFoundError:
            self.engine = None

    def dispose(self):
        if self.engine is not None:
            self.engine.dispose()

    def status(self) -> dict[str, str]:
        if self.engine is None:
            return {"dialect": self.dialect, "status": "driver_unavailable"}
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                if self.dialect == "postgresql" and not self.migration_mode:
                    role = connection.execute(text(
                        "SELECT current_user AS name, rolsuper, rolbypassrls FROM pg_roles WHERE rolname=current_user"
                    )).mappings().one()
                    if role["name"] != "fraudshield_api" or role["rolsuper"] or role["rolbypassrls"]:
                        return {"dialect": self.dialect, "status": "unsafe_runtime_role"}
                if "schema_migrations" not in inspect(connection).get_table_names():
                    return {"dialect": self.dialect, "status": "migrations_required"}
                actual = dict(connection.execute(select(schema_migrations.c.version, schema_migrations.c.checksum)).all())
                if actual != expected_migrations(self.dialect):
                    return {"dialect": self.dialect, "status": "migration_mismatch"}
        except SQLAlchemyError:
            return {"dialect": self.dialect, "status": "unavailable"}
        return {"dialect": self.dialect, "status": "connected"}

    def ensure_ready(self):
        if not self._schema_verified:
            status = self.status()
            if status["status"] != "connected":
                raise APIError(503, "database_unavailable", "Database is unavailable or migrations are not ready")
            self._schema_verified = True

    def _insert(self, model):
        return sqlite_insert(model) if self.dialect == "sqlite" else pg_insert(model)

    @contextmanager
    def owned_session(self, principal: Principal, apply_quota: bool = True):
        self.ensure_ready()
        with Session(self.engine, expire_on_commit=False) as session:
            try:
                with session.begin():
                    if self.dialect == "postgresql":
                        claims = json.dumps({"sub": str(principal.user_id), "role": "authenticated"})
                        session.execute(text("SELECT set_config('request.jwt.claims', :claims, true)"), {"claims": claims})
                        session.execute(text("SELECT set_config('request.jwt.claim.sub', :subject, true)"), {"subject": str(principal.user_id)})
                    session.info["owner_id"] = principal.user_id
                    session.execute(self._insert(User).values(id=principal.user_id).on_conflict_do_nothing(index_elements=[User.id]))
                    if apply_quota:
                        self._enforce_quota(session, principal)
                    yield session
            except APIError:
                raise
            except IntegrityError:
                raise APIError(409, "storage_constraint_error", "Record violates a storage constraint") from None
            except SQLAlchemyError:
                raise APIError(503, "database_unavailable", "Database operation failed") from None

    def _enforce_quota(self, session: Session, principal: Principal):
        now = time.time()
        window = int(now // 60)
        key = hashlib.sha256(f"user:{principal.user_id}".encode()).hexdigest()
        statement = self._insert(APIRateLimitBucket).values(key_sha256=key, window_start=window, request_count=1)
        statement = statement.on_conflict_do_update(
            index_elements=[APIRateLimitBucket.key_sha256],
            set_={
                "window_start": window,
                "updated_at": func.now(),
                "request_count": case(
                    (APIRateLimitBucket.window_start == window, APIRateLimitBucket.request_count + 1), else_=1,
                ),
            },
        ).returning(APIRateLimitBucket.request_count)
        count = session.execute(statement).scalar_one()
        if count > self.settings.rate_limit_per_minute:
            retry = max(1, math.ceil((window + 1) * 60 - now))
            raise APIError(429, "rate_limited", "Authenticated request rate limit exceeded", {"Retry-After": str(retry)})


def current_session(request: Request, principal: Principal = Depends(current_principal)):
    with request.app.state.database.owned_session(principal) as session:
        yield session
