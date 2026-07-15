import jwt
import pytest
from fastapi import HTTPException
from app.services.store import FakeStore
from app.deps import resolve_user_from_auth

SECRET = "test-secret"


@pytest.mark.asyncio
async def test_api_key_resolves():
    store = FakeStore()
    raw, prefix = await store.rotate_api_key("user-1")
    uid = await resolve_user_from_auth(f"Bearer {raw}", store, SECRET)
    assert uid == "user-1"


@pytest.mark.asyncio
async def test_bad_api_key_401():
    store = FakeStore()
    await store.rotate_api_key("user-1")
    with pytest.raises(HTTPException) as ei:
        await resolve_user_from_auth("Bearer sk_totallywrongkey", store, SECRET)
    assert ei.value.status_code == 401


@pytest.mark.asyncio
async def test_jwt_resolves():
    store = FakeStore()
    token = jwt.encode({"sub": "user-9", "aud": "authenticated"}, SECRET, algorithm="HS256")
    uid = await resolve_user_from_auth(f"Bearer {token}", store, SECRET)
    assert uid == "user-9"


@pytest.mark.asyncio
async def test_junk_token_401():
    store = FakeStore()
    with pytest.raises(HTTPException) as ei:
        await resolve_user_from_auth("Bearer not.a.jwt", store, SECRET)
    assert ei.value.status_code == 401


@pytest.mark.asyncio
async def test_missing_header_401():
    store = FakeStore()
    with pytest.raises(HTTPException) as ei:
        await resolve_user_from_auth("", store, SECRET)
    assert ei.value.status_code == 401
