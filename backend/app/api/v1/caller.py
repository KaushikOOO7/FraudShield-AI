from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from starlette.concurrency import run_in_threadpool

from backend.app.core.security import Principal, current_principal
from backend.app.database.workflow import authorize_submission, persist_submission
from backend.app.schemas.caller import CallerRequest
from backend.app.schemas.investigation import ERROR_RESPONSES, InvestigationResponse

router = APIRouter(prefix="/api/v1/analyze", tags=["analysis"], responses=ERROR_RESPONSES)


@router.post("/caller", status_code=201, response_model=InvestigationResponse)
async def analyze_caller(submission: CallerRequest, request: Request, response: Response, principal: Principal = Depends(current_principal)):
    database = request.app.state.database
    await run_in_threadpool(authorize_submission, database, principal, submission.device_id)
    bundle = await request.app.state.caller_service.analyze(submission, principal.user_id)
    result = await run_in_threadpool(persist_submission, database, principal, bundle, submission, UUID(request.state.request_id))
    response.headers["Location"] = f"/api/v1/investigations/{result.investigation_id}"
    return result
