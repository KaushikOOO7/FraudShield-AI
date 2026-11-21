from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from backend.app.core.security import Principal, current_principal
from backend.app.database.community import CommunityRepository
from backend.app.database.connection import current_session
from backend.app.schemas.community import (
    AlertList, AlertPreferences, AlertPreferencesPatch, ReportList, ReportRequest,
    ReportResponse, WatchlistList, WatchlistRequest, WatchlistResponse,
)
from backend.app.schemas.investigation import ERROR_RESPONSES

router = APIRouter(prefix="/api/v1", tags=["user records"], responses=ERROR_RESPONSES)


def repository(request, session, principal):
    return CommunityRepository(session, principal.user_id, request.app.state.settings.community_report_retention_days)


@router.post("/reports", response_model=ReportResponse, status_code=201)
def create_report(submission: ReportRequest, request: Request, response: Response, principal: Principal = Depends(current_principal), session: Session = Depends(current_session, scope="function")):
    result = repository(request, session, principal).create_report(submission, UUID(request.state.request_id))
    response.headers["Location"] = f"/api/v1/reports/{result.id}"
    return result


@router.get("/reports", response_model=ReportList)
def list_reports(request: Request, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0, le=10000), principal: Principal = Depends(current_principal), session: Session = Depends(current_session, scope="function")):
    return repository(request, session, principal).list_reports(limit, offset, UUID(request.state.request_id))


@router.get("/reports/{record_id}", response_model=ReportResponse)
def get_report(record_id: UUID, request: Request, principal: Principal = Depends(current_principal), session: Session = Depends(current_session, scope="function")):
    return repository(request, session, principal).get_report(record_id, UUID(request.state.request_id))


@router.post("/watchlist", response_model=WatchlistResponse, status_code=201, responses={200: {"model": WatchlistResponse}})
def add_watchlist(submission: WatchlistRequest, request: Request, response: Response, principal: Principal = Depends(current_principal), session: Session = Depends(current_session, scope="function")):
    result, created = repository(request, session, principal).add_watchlist(submission, UUID(request.state.request_id))
    response.status_code = 201 if created else 200
    return result


@router.get("/watchlist", response_model=WatchlistList)
def list_watchlist(request: Request, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0, le=10000), principal: Principal = Depends(current_principal), session: Session = Depends(current_session, scope="function")):
    return repository(request, session, principal).list_watchlist(limit, offset, UUID(request.state.request_id))


@router.delete("/watchlist/{record_id}", status_code=204, response_class=Response)
def delete_watchlist(record_id: UUID, request: Request, principal: Principal = Depends(current_principal), session: Session = Depends(current_session, scope="function")):
    repository(request, session, principal).delete_watchlist(record_id, UUID(request.state.request_id))
    return Response(status_code=204)


@router.get("/alerts", response_model=AlertList)
def list_alerts(request: Request, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0, le=10000), principal: Principal = Depends(current_principal), session: Session = Depends(current_session, scope="function")):
    return repository(request, session, principal).list_alerts(limit, offset, UUID(request.state.request_id))


@router.patch("/alerts/preferences", response_model=AlertPreferences)
def set_preferences(preferences: AlertPreferencesPatch, request: Request, principal: Principal = Depends(current_principal), session: Session = Depends(current_session, scope="function")):
    return repository(request, session, principal).set_preferences(preferences, UUID(request.state.request_id))
