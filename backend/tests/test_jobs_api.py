import httpx
import pytest
from httpx import ASGITransport

from app.main import create_app
from app.services.store import FakeStore
from app.deps import get_current_user


class FakeRunner:
    def __init__(self):
        self.submitted = []

    def submit(self, job_id, user_id):
        self.submitted.append((job_id, user_id))


class FakeSettings:
    supabase_jwt_secret = "test-secret"
    cors_origins = ["http://localhost:3000"]


def build():
    store = FakeStore()
    runner = FakeRunner()
    app = create_app(store=store, runner=runner, settings=FakeSettings())
    app.dependency_overrides[get_current_user] = lambda: "test-user"
    return app, store, runner


def client_for(app):
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_create_list_get_results_cancel_flow():
    app, store, runner = build()
    async with client_for(app) as client:
        # create
        resp = await client.post("/v1/jobs", json={"urls": ["http://a", "http://b"]})
        assert resp.status_code == 200
        job = resp.json()
        assert job["status"] == "queued" and job["total"] == 2
        assert runner.submitted == [(job["id"], "test-user")]

        # list
        resp = await client.get("/v1/jobs")
        assert resp.status_code == 200 and len(resp.json()) == 1

        # get + unknown 404
        assert (await client.get(f"/v1/jobs/{job['id']}")).status_code == 200
        assert (await client.get("/v1/jobs/does-not-exist")).status_code == 404

        # seed a result and fetch it
        await store.add_result(job["id"], "test-user", "http://a", {"x": 1}, "ok")
        resp = await client.get(f"/v1/jobs/{job['id']}/results")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1 and body[0]["data"]["x"] == 1

        # cancel
        resp = await client.post(f"/v1/jobs/{job['id']}/cancel")
        assert resp.status_code == 200 and resp.json()["status"] == "canceled"


@pytest.mark.asyncio
async def test_custom_mode_validation_rejected():
    app, store, runner = build()
    async with client_for(app) as client:
        # custom mode with no fields -> 422 from schema validation
        resp = await client.post("/v1/jobs", json={"urls": ["http://a"], "mode": "custom"})
        assert resp.status_code == 422
