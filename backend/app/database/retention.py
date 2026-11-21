"""Maintenance-only deletion of actual expired investigations and audit metadata."""
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, exists, select, text
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.database.connection import Database
from backend.app.database.graph_cleanup import prune_orphan_graph_nodes
from backend.app.database.models import APIRateLimitBucket, AuditLog, CommunityReport, Domain, Investigation, URLIndicator


def purge_expired(database: Database, now: datetime | None = None) -> dict[str, int]:
    now = now or datetime.now(timezone.utc)
    if database.engine is None:
        raise RuntimeError("Database driver unavailable")
    with Session(database.engine) as session, session.begin():
        if database.dialect == "postgresql":
            row = session.execute(text(
                "SELECT current_user AS name, rolsuper, rolbypassrls, "
                "pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid='public.users'::regclass)) AS table_owner "
                "FROM pg_roles WHERE rolname=current_user"
            )).mappings().one()
            if not database.migration_mode or row["name"] == "fraudshield_api" or not (row["rolsuper"] or row["rolbypassrls"] or row["name"] == row["table_owner"]):
                raise RuntimeError("Retention requires a separate maintenance database role")
        investigations = session.execute(delete(Investigation).where(Investigation.expires_at <= now)).rowcount
        graph_nodes = prune_orphan_graph_nodes(session)
        reports = session.execute(delete(CommunityReport).where(CommunityReport.created_at < now - timedelta(days=database.settings.community_report_retention_days))).rowcount
        domains = session.execute(delete(Domain).where(~exists(select(URLIndicator.id).where(URLIndicator.domain_id == Domain.id)))).rowcount
        audits = session.execute(delete(AuditLog).where(AuditLog.created_at < now - timedelta(days=database.settings.audit_retention_days))).rowcount
        buckets = session.execute(delete(APIRateLimitBucket).where(APIRateLimitBucket.window_start < int(now.timestamp() // 60) - 2)).rowcount
        return {"investigations_deleted": investigations, "community_reports_deleted": reports, "orphan_graph_nodes_deleted": graph_nodes, "orphan_domains_deleted": domains, "audit_logs_deleted": audits, "old_rate_buckets_deleted": buckets}


def main():
    database = Database(get_settings(), migration_mode=True)
    try:
        print(json.dumps(purge_expired(database), indent=2))
    except Exception as exc:
        raise SystemExit(f"Retention failed ({type(exc).__name__}); verify the maintenance database role and schema") from None
    finally:
        database.dispose()


if __name__ == "__main__":
    main()
