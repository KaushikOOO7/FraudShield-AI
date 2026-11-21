from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.middleware.cors import CORSMiddleware

from backend.app.core.config import Settings, get_settings
from backend.app.core.errors import (
    APIError, api_error_handler, http_error_handler,
    unexpected_error_handler, validation_error_handler,
)
from backend.app.core.logging import configure_logging
from backend.app.core.middleware import RequestSecurityMiddleware
from backend.app.core.security import JWTVerifier
from backend.app.api.v1.auth import router as auth_router
from backend.app.database.connection import Database
from backend.app.intelligence.engine import IntelligenceEngine
from backend.app.ml.inference.sms import SMSInference
from backend.app.services.sms_service import SMSService
from backend.app.services.url_service import URLService
from backend.app.api.v1.sms import router as sms_router
from backend.app.api.v1.urls import router as url_router
from backend.app.api.v1.investigations import router as investigations_router
from backend.app.api.v1.system import router as system_router
from backend.app.api.v1.community import router as community_router
from backend.app.api.v1.qr import router as qr_router
from backend.app.services.qr_service import QRService
from backend.app.services.caller_service import CallerService
from backend.app.api.v1.caller import router as caller_router
from backend.app.api.v1.apk import router as apk_router
from backend.app.services.apk_service import APKService
from backend.app.intelligence.gemini import GeminiInterpreter
from backend.app.api.v1.interpretation import router as interpretation_router

VERSION = "0.1.0"


def create_app(settings: Settings | None = None, http_transport=None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(settings.provider_timeout_seconds),
            follow_redirects=False,
            trust_env=False,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            transport=http_transport,
        ) as client:
            application.state.http_client = client
            application.state.jwt_verifier = JWTVerifier(settings, client)
            application.state.database = Database(settings)
            application.state.sms_model = SMSInference(settings.sms_model_dir)
            application.state.intelligence = IntelligenceEngine(settings, client)
            application.state.url_service = URLService(application.state.intelligence, settings)
            application.state.sms_service = SMSService(application.state.sms_model, application.state.url_service, settings)
            application.state.qr_service = QRService(application.state.url_service, settings)
            application.state.caller_service = CallerService(settings)
            application.state.apk_service = APKService(settings)
            application.state.gemini = GeminiInterpreter(settings, client)
            try:
                yield
            finally:
                application.state.database.dispose()

    application = FastAPI(
        title="FraudShield AI", version=VERSION,
        description="Evidence-based investigation APIs. Unavailable capabilities are explicit.",
        lifespan=lifespan,
    )
    application.state.settings = settings
    application.state.logger = configure_logging()
    application.add_exception_handler(APIError, api_error_handler)
    application.add_exception_handler(RequestValidationError, validation_error_handler)
    application.add_exception_handler(HTTPException, http_error_handler)
    application.add_exception_handler(Exception, unexpected_error_handler)
    if settings.cors_origins:
        application.add_middleware(
            CORSMiddleware, allow_origins=settings.cors_origins,
            allow_methods=["GET", "POST", "DELETE", "PATCH"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
            expose_headers=["X-Request-ID", "Retry-After"],
        )
    application.add_middleware(RequestSecurityMiddleware, settings=settings)
    application.include_router(auth_router)
    application.include_router(sms_router)
    application.include_router(url_router)
    application.include_router(investigations_router)
    application.include_router(system_router)
    application.include_router(community_router)
    application.include_router(qr_router)
    application.include_router(caller_router)
    application.include_router(apk_router)
    application.include_router(interpretation_router)

    @application.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "FraudShield AI", "version": VERSION}

    return application


app = create_app()
