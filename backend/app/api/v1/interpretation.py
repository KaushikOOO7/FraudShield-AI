from uuid import UUID

from fastapi import APIRouter, Depends, Request
from starlette.concurrency import run_in_threadpool

from backend.app.core.security import Principal, current_principal
from backend.app.database.interpretation import load_interpretation_subject, persist_interpretation
from backend.app.schemas.interpretation import InterpretationRequest, InterpretationResponse
from backend.app.schemas.investigation import ERROR_RESPONSES

router = APIRouter(prefix="/api/v1/investigations", tags=["interpretation"], responses=ERROR_RESPONSES)


@router.post("/{investigation_id}/interpret", response_model=InterpretationResponse)
async def interpret_investigation(investigation_id: UUID, submission: InterpretationRequest, request: Request, principal: Principal = Depends(current_principal)):
    request_id = UUID(request.state.request_id)
    database = request.app.state.database
    investigation = await run_in_threadpool(load_interpretation_subject, database, principal, investigation_id, request_id)
    result = await request.app.state.gemini.interpret(investigation, submission.use_gemini)
    return await run_in_threadpool(persist_interpretation, database, principal, result, submission.use_gemini, request_id)
