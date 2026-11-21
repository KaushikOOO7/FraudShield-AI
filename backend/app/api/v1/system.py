from fastapi import APIRouter, Depends, Request

from backend.app.core.security import Principal, current_principal
from backend.app.schemas.investigation import ContractModel, ERROR_RESPONSES
from backend.app.services.apk_service import parser_available

router = APIRouter(prefix="/api/v1/system", tags=["system"], responses=ERROR_RESPONSES)


class SystemStatus(ContractModel):
    version: str
    environment: str
    database: dict[str, str]
    authentication: str
    sms_model: dict
    providers: list[dict]
    capabilities: dict[str, str]


@router.get("/status", response_model=SystemStatus)
def system_status(request: Request, principal: Principal = Depends(current_principal)) -> SystemStatus:
    return SystemStatus(
        version=request.app.version, environment=request.app.state.settings.app_env,
        database=request.app.state.database.status(), authentication="token_verified",
        sms_model=request.app.state.sms_model.system_status(), providers=request.app.state.intelligence.system_status(),
        capabilities={
            "sms_investigation": "implemented", "url_structure_analysis": "implemented",
            "url_ml": request.app.state.url_service.model.status, "langgraph": "not_implemented",
            "gemini": request.app.state.gemini.last_status or ("configured_not_verified" if request.app.state.gemini.configured else "provider_not_configured"),
            "apk_analysis": "static_adapter_unverified" if parser_available() else "parser_unavailable", "qr_analysis": "isolated_decoding_url_upi_syntax", "caller_intelligence": "format_only_reputation_unavailable",
            "brand_impersonation": "not_implemented", "cross_channel_correlation": "observed_url_identifiers_across_channels",
            "community_reports_api": "owner_scoped_unreviewed", "watchlist_api": "implemented",
            "alerts_api": "opt_in_in_app_history", "supabase_storage": "not_implemented",
        },
    )
