import pytest
from unittest.mock import MagicMock

from app.services.supabase_store import SupabaseStore


@pytest.mark.asyncio
async def test_create_job_inserts_and_returns_row():
    client = MagicMock()
    exec_res = MagicMock()
    exec_res.data = [{"id": "job-1", "user_id": "u", "status": "queued",
                      "config": {}, "total": 1, "completed": 0, "failed": 0}]
    client.table.return_value.insert.return_value.execute.return_value = exec_res

    store = SupabaseStore(client)
    job = await store.create_job("u", {"urls": ["x"]}, total=1)

    assert job["id"] == "job-1"
    client.table.assert_any_call("jobs")


@pytest.mark.asyncio
async def test_get_job_scopes_by_user_and_returns_row():
    client = MagicMock()
    exec_res = MagicMock()
    exec_res.data = [{"id": "job-1", "user_id": "u"}]
    (client.table.return_value.select.return_value
     .eq.return_value.eq.return_value.limit.return_value.execute.return_value) = exec_res

    store = SupabaseStore(client)
    job = await store.get_job("job-1", "u")
    assert job is not None and job["id"] == "job-1"


@pytest.mark.asyncio
async def test_bump_job_progress_uses_atomic_rpc():
    client = MagicMock()
    store = SupabaseStore(client)
    await store.bump_job_progress("job-1", ok=True)
    client.rpc.assert_called_once_with("bump_job_progress", {"p_job_id": "job-1", "p_ok": True})


@pytest.mark.asyncio
async def test_increment_usage_uses_atomic_rpc():
    client = MagicMock()
    store = SupabaseStore(client)
    await store.increment_usage("u", 4)
    client.rpc.assert_called_once_with("increment_usage", {"p_user_id": "u", "p_n": 4})
