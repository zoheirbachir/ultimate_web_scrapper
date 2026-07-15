import httpx
import pytest
from httpx import ASGITransport

from app.main import create_app
from app.services.store import FakeStore
from app.deps import get_current_user


class FakeRunner:
    def submit(self, job_id, user_id):
        pass


class FakeSettings:
    supabase_jwt_secret = "test-secret"
    cors_origins = ["http://localhost:3000"]


def build():
    store = FakeStore()
    app = create_app(store=store, runner=FakeRunner(), settings=FakeSettings())
    app.dependency_overrides[get_current_user] = lambda: "u"
    return app, store


def _client(app):
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_rotate_key_returns_sk_and_updates_prefix():
    app, store = build()
    async with _client(app) as client:
        resp = await client.post("/v1/keys/rotate")
        assert resp.status_code == 200
        body = resp.json()
        assert body["api_key"].startswith("sk_")
        assert len(body["prefix"]) == 12
        prof = await store.get_profile("u")
        assert prof["api_key_prefix"] == body["prefix"]


@pytest.mark.asyncio
async def test_usage_returns_count():
    app, store = build()
    await store.increment_usage("u", 5)
    async with _client(app) as client:
        resp = await client.get("/v1/usage")
        assert resp.status_code == 200
        assert resp.json()["usage_count"] == 5
