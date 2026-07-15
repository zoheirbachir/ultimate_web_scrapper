from fastapi import APIRouter, Depends, Request

from app.deps import get_current_user
from app.schemas import UsageOut

router = APIRouter(prefix="/v1", tags=["usage"])


@router.get("/usage", response_model=UsageOut)
async def get_usage(request: Request, user_id: str = Depends(get_current_user)):
    prof = await request.app.state.store.get_profile(user_id)
    return UsageOut(usage_count=prof.get("usage_count", 0))
