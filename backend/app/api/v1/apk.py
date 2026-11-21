from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile
from starlette.concurrency import run_in_threadpool

from backend.app.core.errors import APIError
from backend.app.core.security import Principal, current_principal
from backend.app.database.workflow import authorize_submission, persist_submission
from backend.app.schemas.investigation import ERROR_RESPONSES, InvestigationResponse
from backend.app.schemas.requests import SubmissionMetadata

router = APIRouter(prefix="/api/v1/analyze", tags=["analysis"], responses=ERROR_RESPONSES)


@router.post("/apk", status_code=201, response_model=InvestigationResponse)
async def analyze_apk(request: Request, response: Response, file: UploadFile = File(...), source: Literal["android_share", "android_manual", "web_share", "web_manual", "api"] = Form("api"), principal: Principal = Depends(current_principal)):
    submission = SubmissionMetadata(source=source)
    await run_in_threadpool(authorize_submission, request.app.state.database, principal, None)
    try:
        if file.content_type not in ("application/vnd.android.package-archive", "application/octet-stream"):
            raise APIError(415, "unsupported_apk_type", "Use an Android APK archive")
        data = await file.read(request.app.state.settings.apk_max_upload_bytes + 1)
        if len(data) > request.app.state.settings.apk_max_upload_bytes:
            raise APIError(413, "file_too_large", "APK exceeds the upload limit")
        bundle = await request.app.state.apk_service.analyze(data, submission, principal.user_id)
    finally:
        await file.close()
    result = await run_in_threadpool(persist_submission, request.app.state.database, principal, bundle, submission, UUID(request.state.request_id))
    response.headers["Location"] = f"/api/v1/investigations/{result.investigation_id}"
    return result
