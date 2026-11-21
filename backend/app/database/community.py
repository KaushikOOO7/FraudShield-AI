from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from backend.app.core.errors import APIError
from backend.app.database import models
from backend.app.schemas.community import (
    AlertList, AlertPreferences, AlertResponse, ReportList, ReportResponse,
    WatchlistList, WatchlistResponse,
)
from backend.app.utils.indicators import normalized_indicator
from backend.app.utils.privacy import redact_text


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value is not None and value.tzinfo is None else value


class CommunityRepository:
    def __init__(self, session, owner_id: UUID, report_retention_days=30):
        if session.info.get("owner_id") != owner_id:
            raise APIError(403, "ownership_error", "Database ownership context does not match")
        self.session, self.owner_id = session, owner_id
        self.report_cutoff = datetime.now(timezone.utc) - timedelta(days=report_retention_days)

    def audit(self, action, resource, request_id):
        self.session.add(models.AuditLog(owner_id=self.owner_id, action=action, resource_id=resource, request_id=request_id))

    def _page(self, statement, model, limit, offset):
        return self.session.scalars(statement.order_by(model.created_at.desc(), model.id.desc()).offset(offset).limit(limit + 1)).all()

    @staticmethod
    def watch_response(row):
        return WatchlistResponse(id=row.id, indicator_type=row.indicator_type, redacted_value=row.redacted_value, created_at=utc(row.created_at))

    @staticmethod
    def report_response(row):
        return ReportResponse(id=row.id, subject_type=row.subject_type, redacted_subject=row.redacted_subject, redacted_description=row.redacted_description, moderation_status=row.moderation_status, verified_at=utc(row.verified_at), created_at=utc(row.created_at))

    def add_watchlist(self, submission, request_id):
        value, digest = normalized_indicator(submission.indicator_type, submission.value)
        row = self.session.scalar(select(models.Watchlist).where(models.Watchlist.owner_id == self.owner_id, models.Watchlist.indicator_type == submission.indicator_type, models.Watchlist.value_sha256 == digest))
        created = row is None
        if created:
            insert = sqlite_insert if self.session.bind.dialect.name == "sqlite" else pg_insert
            row_id = self.session.execute(insert(models.Watchlist).values(owner_id=self.owner_id, indicator_type=submission.indicator_type, redacted_value=value, value_sha256=digest).on_conflict_do_nothing(index_elements=[models.Watchlist.owner_id, models.Watchlist.indicator_type, models.Watchlist.value_sha256]).returning(models.Watchlist.id)).scalar_one_or_none()
            created = row_id is not None
            row = self.session.scalar(select(models.Watchlist).where(models.Watchlist.owner_id == self.owner_id, models.Watchlist.indicator_type == submission.indicator_type, models.Watchlist.value_sha256 == digest))
        self.audit("watchlist.created" if created else "watchlist.existing", row.id, request_id)
        return self.watch_response(row), created

    def list_watchlist(self, limit, offset, request_id):
        rows = self._page(select(models.Watchlist).where(models.Watchlist.owner_id == self.owner_id), models.Watchlist, limit, offset)
        self.audit("watchlist.listed", None, request_id)
        return WatchlistList(items=[self.watch_response(row) for row in rows[:limit]], limit=limit, offset=offset, has_more=len(rows) > limit)

    def delete_watchlist(self, record_id, request_id):
        row = self.session.scalar(select(models.Watchlist).where(models.Watchlist.id == record_id, models.Watchlist.owner_id == self.owner_id))
        if row is None:
            raise APIError(404, "watchlist_not_found", "Watchlist entry was not found")
        self.session.delete(row)
        self.audit("watchlist.deleted", row.id, request_id)

    def create_report(self, submission, request_id):
        value, _ = normalized_indicator(submission.subject_type, submission.subject)
        row = models.CommunityReport(owner_id=self.owner_id, subject_type=submission.subject_type, redacted_subject=value, redacted_description=redact_text(submission.description), moderation_status="unreviewed")
        self.session.add(row)
        self.session.flush()
        self.audit("report.created", row.id, request_id)
        return self.report_response(row)

    def _reports(self):
        return select(models.CommunityReport).where(models.CommunityReport.owner_id == self.owner_id, models.CommunityReport.created_at >= self.report_cutoff)

    def list_reports(self, limit, offset, request_id):
        rows = self._page(self._reports(), models.CommunityReport, limit, offset)
        self.audit("report.listed", None, request_id)
        return ReportList(items=[self.report_response(row) for row in rows[:limit]], limit=limit, offset=offset, has_more=len(rows) > limit)

    def get_report(self, record_id, request_id):
        row = self.session.scalar(self._reports().where(models.CommunityReport.id == record_id))
        if row is None:
            raise APIError(404, "report_not_found", "Report was not found")
        self.audit("report.read", row.id, request_id)
        return self.report_response(row)

    def set_preferences(self, preferences, request_id):
        insert = sqlite_insert if self.session.bind.dialect.name == "sqlite" else pg_insert
        values = preferences.model_dump()
        self.session.execute(insert(models.UserProfile).values(owner_id=self.owner_id, alert_preferences=values).on_conflict_do_update(index_elements=[models.UserProfile.owner_id], set_={"alert_preferences": values, "updated_at": datetime.now(timezone.utc)}))
        self.audit("alerts.preferences_updated", None, request_id)
        return AlertPreferences(**values)

    def list_alerts(self, limit, offset, request_id):
        statement = select(models.SecurityAlert).join(models.Investigation, (models.Investigation.id == models.SecurityAlert.investigation_id) & (models.Investigation.owner_id == models.SecurityAlert.owner_id)).where(models.SecurityAlert.owner_id == self.owner_id, models.Investigation.expires_at > datetime.now(timezone.utc))
        rows = self._page(statement, models.SecurityAlert, limit, offset)
        self.audit("alerts.listed", None, request_id)
        return AlertList(items=[AlertResponse(id=row.id, investigation_id=row.investigation_id, severity=row.severity, message=row.message, created_at=utc(row.created_at), read_at=utc(row.read_at)) for row in rows[:limit]], limit=limit, offset=offset, has_more=len(rows) > limit)
