import pytest
from app.services.store import FakeStore


@pytest.mark.asyncio
async def test_job_lifecycle_and_ownership():
    store = FakeStore()
    uid = "user-1"
    job = await store.create_job(uid, {"urls": ["http://a"], "mode": "auto"}, total=1)
    assert job["status"] == "queued"
    assert job["total"] == 1

    assert (await store.get_job(job["id"], uid))["id"] == job["id"]
    assert await store.get_job(job["id"], "other-user") is None  # ownership scoped

    await store.set_job_status(job["id"], "running", started=True)
    await store.add_result(job["id"], uid, "http://a", {"x": 1}, "ok")
    await store.bump_job_progress(job["id"], ok=True)

    results = await store.list_results(job["id"], uid)
    assert len(results) == 1 and results[0]["data"]["x"] == 1
    assert (await store.get_job(job["id"], uid))["completed"] == 1

    await store.set_job_status(job["id"], "completed", finished=True)
    done = await store.get_job(job["id"], uid)
    assert done["status"] == "completed" and done["finished_at"] is not None


@pytest.mark.asyncio
async def test_rotate_key_and_usage():
    store = FakeStore()
    uid = "user-2"
    raw, prefix = await store.rotate_api_key(uid)
    assert raw.startswith("sk_")
    prof = await store.get_profile_by_api_key_prefix(prefix)
    assert prof is not None and prof["id"] == uid
    await store.increment_usage(uid, 3)
    assert (await store.get_profile(uid))["usage_count"] == 3


@pytest.mark.asyncio
async def test_list_jobs_newest_first_and_reset_running():
    store = FakeStore()
    uid = "user-3"
    j1 = await store.create_job(uid, {"urls": [], "mode": "auto"}, total=0)
    j2 = await store.create_job(uid, {"urls": [], "mode": "auto"}, total=0)
    jobs = await store.list_jobs(uid)
    assert [j["id"] for j in jobs][:2] == [j2["id"], j1["id"]]  # newest first

    await store.set_job_status(j1["id"], "running", started=True)
    n = await store.reset_running_jobs()
    assert n == 1
    assert (await store.get_job(j1["id"], uid))["status"] == "queued"
