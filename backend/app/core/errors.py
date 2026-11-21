from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException


class APIError(Exception):
    def __init__(self, status_code: int, code: str, message: str, headers: dict | None = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.headers = headers or {}
        super().__init__(code)


def error_body(code: str, message: str, request_id: str, details: list | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or [], "request_id": request_id}}


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(exc.code, exc.message, request.state.request_id),
        headers=exc.headers,
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Pydantic's default response reflects raw input and may leak OTPs or credentials.
    permitted_fields = {"body", "query", "path", "header", "content", "url", "source", "device_id", "use_threat_intelligence", "use_gemini", "phone_number", "file", "limit", "offset", "investigation_id", "record_id", "subject_type", "subject", "description", "indicator_type", "value", "high_risk_alerts"}
    details = [{"field": ".".join(str(x) if isinstance(x, int) or x in permitted_fields else "unknown_field" for x in item["loc"]), "message": "Invalid value"} for item in exc.errors()]
    sensitive = any(item["type"] == "sensitive_input" for item in exc.errors())
    return JSONResponse(
        status_code=422,
        content=error_body("sensitive_input" if sensitive else "validation_error", "Remove sensitive credentials before submission" if sensitive else "Request validation failed", request.state.request_id, details),
    )


async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    codes = {404: "not_found", 405: "method_not_allowed"}
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(codes.get(exc.status_code, "http_error"), "Request cannot be handled", request.state.request_id),
        headers=exc.headers,
    )


async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # Exception strings can contain connection URLs, API keys, or message text.
    request.app.state.logger.error("request_failed", extra={"request_id": request.state.request_id})
    return JSONResponse(
        status_code=500,
        content=error_body("internal_error", "An internal error occurred", request.state.request_id),
        headers={"X-Request-ID": request.state.request_id, "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )
