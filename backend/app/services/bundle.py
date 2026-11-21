from dataclasses import dataclass, field
from uuid import UUID

from backend.app.intelligence.base import ProviderOutcome
from backend.app.schemas.investigation import InvestigationResponse
from backend.app.utils.urls import ParsedURL


@dataclass
class InvestigationBundle:
    response: InvestigationResponse
    urls: list[ParsedURL] = field(default_factory=list)
    provider_results: list[tuple[UUID, ProviderOutcome]] = field(default_factory=list)
    model_manifest: dict | None = None
    qr_analysis: dict | None = None
    apk_analysis: dict | None = None
    model_manifests: dict[str, dict] = field(default_factory=dict)
