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


@router.post("/qr", status_code=201, response_model=InvestigationResponse)
async def analyze_qr(
    request: Request, response: Response, file: UploadFile = File(...),
    source: Literal["android_share", "android_manual", "web_share", "web_manual", "api"] = Form("api"),
    use_threat_intelligence: Literal["true", "false"] = Form("false"),
    principal: Principal = Depends(current_principal),
):
    submission = SubmissionMetadata(source=source, use_threat_intelligence=use_threat_intelligence == "true")
    await run_in_threadpool(authorize_submission, request.app.state.database, principal, None)
    try:
        if file.content_type not in ("image/png", "image/jpeg"):
            raise APIError(415, "unsupported_image_type", "Use a PNG or JPEG image")
        data = await file.read(request.app.state.settings.qr_max_upload_bytes + 1)
        if len(data) > request.app.state.settings.qr_max_upload_bytes:
            raise APIError(413, "file_too_large", "QR image exceeds the upload limit")
        expected = b"\x89PNG\r\n\x1a\n" if file.content_type == "image/png" else b"\xff\xd8\xff"
        if not data.startswith(expected):
            raise APIError(422, "invalid_image", "Image signature does not match its media type")
        bundle = await request.app.state.qr_service.analyze(data, submission, principal.user_id)
    finally:
        await file.close()
    result = await run_in_threadpool(persist_submission, request.app.state.database, principal, bundle, submission, UUID(request.state.request_id))
    response.headers["Location"] = f"/api/v1/investigations/{result.investigation_id}"
    return result
