import jwt


def verify_supabase_jwt(token: str, secret: str) -> str:
    """Verify a Supabase access token (HS256 or ES256, aud=authenticated) and return the
    user id (the `sub` claim). Raises jwt exceptions on any failure."""
    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "HS256")
    except Exception:
        alg = "HS256"

    if alg == "ES256":
        try:
            from app.config import get_settings
            supabase_url = get_settings().supabase_url
            jwks_url = f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
            jwk_client = jwt.PyJWKClient(jwks_url)
            signing_key = jwk_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(token, signing_key.key, algorithms=["ES256"], audience="authenticated")
        except Exception as e:
            raise jwt.InvalidSignatureError(f"ES256 signature verification failed: {e}")
    else:
        try:
            # Try verifying with the original secret string first (useful for test configs)
            payload = jwt.decode(token, secret, algorithms=["HS256"], audience="authenticated")
        except jwt.InvalidSignatureError:
            # If signature check fails, try base64-decoding the secret key (real Supabase keys are base64)
            try:
                import base64
                # Add padding if missing
                padded_secret = secret
                missing_padding = len(secret) % 4
                if missing_padding:
                    padded_secret += '=' * (4 - missing_padding)
                decoded_secret = base64.b64decode(padded_secret)
                payload = jwt.decode(token, decoded_secret, algorithms=["HS256"], audience="authenticated")
            except Exception:
                raise jwt.InvalidSignatureError("Signature verification failed with both plain and base64 keys")

    user_id = payload.get("sub")
    if not user_id:
        raise jwt.InvalidTokenError("token missing sub claim")
    return user_id
