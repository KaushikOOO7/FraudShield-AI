from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.app.core.security import Principal, current_principal
from backend.app.schemas.investigation import ERROR_RESPONSES

router = APIRouter(prefix="/api/v1/auth", tags=["auth"], responses=ERROR_RESPONSES)


class IdentityResponse(BaseModel):
    user_id: UUID


@router.get("/me", response_model=IdentityResponse)
def identity(principal: Principal = Depends(current_principal)) -> IdentityResponse:
    return IdentityResponse(user_id=principal.user_id)
