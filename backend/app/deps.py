from fastapi import Depends, HTTPException, Request

from app.core.apikeys import PREFIX_LEN, verify_api_key
from app.core.security import verify_supabase_jwt
from app.services.store import Store


async def resolve_user_from_auth(authorization: str, store: Store, jwt_secret: str) -> str:
    """Resolve an Authorization header to a user id. `sk_`-prefixed bearer tokens are
    API keys (looked up by prefix + verified against the stored hash); anything else is
    treated as a Supabase JWT. Raises HTTP 401 on any failure."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()

    if token.startswith("sk_"):
        prefix = token[:PREFIX_LEN]
        prof = await store.get_profile_by_api_key_prefix(prefix)
        if not prof or not verify_api_key(token, prof.get("api_key_hash") or ""):
            raise HTTPException(status_code=401, detail="Invalid API key")
        return prof["id"]

    try:
        user_id = verify_supabase_jwt(token, jwt_secret)
        print(f"[AUTH DIAGNOSTIC] Successfully verified token for user_id: {user_id}")
        return user_id
    except Exception as e:
        import traceback
        print(f"[AUTH DIAGNOSTIC] Token verification failed!")
        print(f"  Token length: {len(token)}")
        print(f"  Token prefix: '{token[:30]}...'")
        print(f"  Error message: {str(e)}")
        # print(traceback.format_exc())
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def get_current_user(request: Request) -> str:
    """FastAPI dependency: resolve the caller from app.state.store + settings."""
    store: Store = request.app.state.store
    jwt_secret: str = request.app.state.settings.supabase_jwt_secret
    return await resolve_user_from_auth(request.headers.get("authorization", ""), store, jwt_secret)
