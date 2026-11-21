from datetime import datetime, timezone

from sqlalchemy import select

from backend.app.core.errors import APIError
from backend.app.database.models import AuditLog, Investigation, InvestigationEvent
from backend.app.database.repositories import InvestigationRepository


def load_interpretation_subject(database, principal, investigation_id, request_id):
    with database.owned_session(principal) as session:
        return InvestigationRepository(session, principal.user_id).get(investigation_id, request_id)


def persist_interpretation(database, principal, outcome, requested, request_id):
    with database.owned_session(principal, apply_quota=False) as session:
        row = session.scalar(select(Investigation.id).where(Investigation.id == outcome.investigation_id, Investigation.owner_id == principal.user_id, Investigation.expires_at > datetime.now(timezone.utc)))
        if row is None:
            raise APIError(404, "investigation_not_found", "Investigation was not found")
        session.add(InvestigationEvent(owner_id=principal.user_id, investigation_id=outcome.investigation_id, event_type="interpretation.checked", details={"provider": outcome.provider, "status": outcome.status, "requested": requested, "model_used": outcome.model_used, "checked_at": outcome.checked_at.isoformat(), "selected_finding_ids": [str(item.id) for item in outcome.selected_findings]}))
        session.add(AuditLog(owner_id=principal.user_id, action="investigation.interpreted", resource_id=outcome.investigation_id, request_id=request_id))
    return outcome
