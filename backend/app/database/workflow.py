"""Short authorization and persistence transactions, separated from network analysis."""
from uuid import UUID

from backend.app.core.security import Principal
from backend.app.database.repositories import InvestigationRepository


def authorize_submission(database, principal: Principal, device_id: UUID | None):
    with database.owned_session(principal) as session:
        InvestigationRepository(session, principal.user_id).check_device(device_id)


def persist_submission(database, principal: Principal, bundle, submission, request_id: UUID):
    with database.owned_session(principal, apply_quota=False) as session:
        repository = InvestigationRepository(session, principal.user_id)
        repository.check_device(submission.device_id)
        result = repository.create(bundle, submission, request_id)
    # The transaction has committed before a successful HTTP response can exist.
    return result
