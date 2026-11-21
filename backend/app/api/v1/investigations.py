from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from backend.app.core.security import Principal, current_principal
from backend.app.database.connection import current_session
from backend.app.database.repositories import InvestigationRepository
from backend.app.database.correlation import CorrelationRepository
from backend.app.schemas.correlation import CorrelationResponse
from backend.app.schemas.investigation import ERROR_RESPONSES, InvestigationList, InvestigationResponse

router = APIRouter(prefix="/api/v1/investigations", tags=["investigations"], responses=ERROR_RESPONSES)


@router.post("/{investigation_id}/correlate", response_model=CorrelationResponse)
def correlate_investigation(
    investigation_id: UUID, request: Request, limit: int = Query(default=20, ge=1, le=100),
    principal: Principal = Depends(current_principal),
    session: Session = Depends(current_session, scope="function"),
) -> CorrelationResponse:
    return CorrelationRepository(session, principal.user_id).correlate(
        investigation_id, limit, UUID(request.state.request_id),
    )


@router.get("", response_model=InvestigationList)
def list_investigations(
    request: Request, limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0, le=10000),
    principal: Principal = Depends(current_principal), session: Session = Depends(current_session, scope="function"),
) -> InvestigationList:
    return InvestigationRepository(session, principal.user_id).list(limit, offset, UUID(request.state.request_id))


@router.get("/{investigation_id}", response_model=InvestigationResponse)
def get_investigation(
    investigation_id: UUID, request: Request, principal: Principal = Depends(current_principal),
    session: Session = Depends(current_session, scope="function"),
) -> InvestigationResponse:
    return InvestigationRepository(session, principal.user_id).get(investigation_id, UUID(request.state.request_id))


@router.delete("/{investigation_id}", status_code=204, response_class=Response)
def delete_investigation(
    investigation_id: UUID, request: Request, principal: Principal = Depends(current_principal),
    session: Session = Depends(current_session, scope="function"),
) -> Response:
    InvestigationRepository(session, principal.user_id).delete(investigation_id, UUID(request.state.request_id))
    return Response(status_code=204)
