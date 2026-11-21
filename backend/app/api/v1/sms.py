from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from starlette.concurrency import run_in_threadpool

from backend.app.core.security import Principal, current_principal
from backend.app.database.workflow import authorize_submission, persist_submission
from backend.app.schemas.investigation import ERROR_RESPONSES, InvestigationResponse
from backend.app.schemas.requests import SMSRequest

router = APIRouter(prefix="/api/v1/analyze", tags=["analysis"], responses=ERROR_RESPONSES)


@router.post("/sms", response_model=InvestigationResponse, status_code=201)
async def analyze_sms(
    submission: SMSRequest, request: Request, response: Response,
    principal: Principal = Depends(current_principal),
) -> InvestigationResponse:
    database = request.app.state.database
    await run_in_threadpool(authorize_submission, database, principal, submission.device_id)
    bundle = await request.app.state.sms_service.analyze(submission, principal.user_id)
    result = await run_in_threadpool(persist_submission, database, principal, bundle, submission, UUID(request.state.request_id))
    response.headers["Location"] = f"/api/v1/investigations/{result.investigation_id}"
    return result
