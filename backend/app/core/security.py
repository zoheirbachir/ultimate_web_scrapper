import jwt


def verify_supabase_jwt(token: str, secret: str) -> str:
    """Verify a Supabase access token (HS256, aud=authenticated) and return the
    user id (the `sub` claim). Raises jwt exceptions on any failure."""
    payload = jwt.decode(token, secret, algorithms=["HS256"], audience="authenticated")
    user_id = payload.get("sub")
    if not user_id:
        raise jwt.InvalidTokenError("token missing sub claim")
    return user_id
