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


async def _setup():
    store = FakeStore()
    app = create_app(store=store, runner=FakeRunner(), settings=FakeSettings())
    app.dependency_overrides[get_current_user] = lambda: "u"
    job = await store.create_job("u", {"urls": ["http://a"], "mode": "custom"}, total=1)
    await store.add_result(job["id"], "u", "http://a", {"title": "Hello", "price": 9.99}, "ok")
    return app, job


def _client(app):
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_export_csv():
    app, job = await _setup()
    async with _client(app) as client:
        resp = await client.get(f"/v1/jobs/{job['id']}/export?format=csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "Hello" in resp.text


@pytest.mark.asyncio
async def test_export_json():
    app, job = await _setup()
    async with _client(app) as client:
        resp = await client.get(f"/v1/jobs/{job['id']}/export?format=json")
        assert resp.status_code == 200
        body = resp.json()
        assert body[0]["title"] == "Hello" and body[0]["url"] == "http://a"


@pytest.mark.asyncio
async def test_export_xlsx():
    app, job = await _setup()
    async with _client(app) as client:
        resp = await client.get(f"/v1/jobs/{job['id']}/export?format=xlsx")
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers["content-type"]
        assert len(resp.content) > 0


@pytest.mark.asyncio
async def test_export_bad_format():
    app, job = await _setup()
    async with _client(app) as client:
        resp = await client.get(f"/v1/jobs/{job['id']}/export?format=pdf")
        assert resp.status_code == 400
