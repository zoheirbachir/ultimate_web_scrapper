import hashlib
import hmac
import secrets
from typing import Tuple

PREFIX_LEN = 12


def hash_api_key(raw: str) -> str:
    """Return the sha256 hex digest of a raw API key (what we store)."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def generate_api_key() -> Tuple[str, str, str]:
    """Generate a new key. Returns (raw, prefix, hash). The raw key is shown to the
    user exactly once; only the prefix (for display) and hash (for verification) are
    persisted."""
    raw = "sk_" + secrets.token_urlsafe(32)
    return raw, raw[:PREFIX_LEN], hash_api_key(raw)


def verify_api_key(raw: str, hashed: str) -> bool:
    """Constant-time check that a raw key matches a stored hash."""
    if not raw or not hashed:
        return False
    return hmac.compare_digest(hash_api_key(raw), hashed)
