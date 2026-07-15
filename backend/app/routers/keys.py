from fastapi import APIRouter, Depends, Request

from app.deps import get_current_user
from app.schemas import KeyOut

router = APIRouter(prefix="/v1", tags=["keys"])


@router.post("/keys/rotate", response_model=KeyOut)
async def rotate_key(request: Request, user_id: str = Depends(get_current_user)):
    """Generate a fresh API key. The raw key is returned exactly once; only its prefix
    and hash are stored."""
    raw, prefix = await request.app.state.store.rotate_api_key(user_id)
    return KeyOut(api_key=raw, prefix=prefix)
