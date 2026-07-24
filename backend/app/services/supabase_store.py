import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.core.apikeys import generate_api_key


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SupabaseStore:
    """Production Store backed by Supabase Postgres via supabase-py.

    supabase-py is synchronous, so every call is offloaded to a worker thread to
    avoid blocking the FastAPI event loop. Writes use the service-role client and
    scope every query by user_id explicitly (RLS is a second line of defence for
    the browser read path, not relied on here)."""

    def __init__(self, client):
        self.client = client

    async def _run(self, fn):
        return await asyncio.to_thread(fn)

    async def create_job(self, user_id: str, config: Dict[str, Any], total: int) -> Dict[str, Any]:
        payload = {"user_id": user_id, "status": "queued", "config": config, "total": total}
        res = await self._run(lambda: self.client.table("jobs").insert(payload).execute())
        return res.data[0]

    async def get_job(self, job_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        res = await self._run(lambda: self.client.table("jobs").select("*")
                              .eq("id", job_id).eq("user_id", user_id).limit(1).execute())
        return res.data[0] if res.data else None

    async def list_jobs(self, user_id: str) -> List[Dict[str, Any]]:
        res = await self._run(lambda: self.client.table("jobs").select("*")
                              .eq("user_id", user_id).order("created_at", desc=True).execute())
        return res.data or []

    async def set_job_status(self, job_id: str, status: str, error: Optional[str] = None,
                             started: bool = False, finished: bool = False) -> None:
        patch: Dict[str, Any] = {"status": status}
        if error is not None:
            patch["error"] = error
        if started:
            patch["started_at"] = _now()
        if finished:
            patch["finished_at"] = _now()
        await self._run(lambda: self.client.table("jobs").update(patch).eq("id", job_id).execute())

    async def bump_job_progress(self, job_id: str, ok: bool) -> None:
        await self._run(lambda: self.client.rpc(
            "bump_job_progress", {"p_job_id": job_id, "p_ok": ok}).execute())

    async def add_result(self, job_id: str, user_id: str, url: str,
                         data: Optional[Dict[str, Any]], status: str,
                         error: Optional[str] = None) -> Dict[str, Any]:
        payload = {"job_id": job_id, "user_id": user_id, "url": url,
                   "data": data, "status": status, "error": error}
        res = await self._run(lambda: self.client.table("results").insert(payload).execute())
        return res.data[0]

    async def list_results(self, job_id: str, user_id: str) -> List[Dict[str, Any]]:
        res = await self._run(lambda: self.client.table("results").select("*")
                              .eq("job_id", job_id).eq("user_id", user_id)
                              .order("scraped_at", desc=False).execute())
        return res.data or []

    async def get_profile(self, user_id: str) -> Dict[str, Any]:
        res = await self._run(lambda: self.client.table("profiles").select("*")
                              .eq("id", user_id).limit(1).execute())
        if res.data:
            return res.data[0]
        return {"id": user_id, "api_key_hash": None, "api_key_prefix": None, "usage_count": 0}

    async def get_profile_by_api_key_prefix(self, prefix: str) -> Optional[Dict[str, Any]]:
        res = await self._run(lambda: self.client.table("profiles").select("*")
                              .eq("api_key_prefix", prefix).limit(1).execute())
        return res.data[0] if res.data else None

    async def rotate_api_key(self, user_id: str) -> Tuple[str, str]:
        raw, prefix, hashed = generate_api_key()
        await self._run(lambda: self.client.table("profiles")
                        .update({"api_key_hash": hashed, "api_key_prefix": prefix})
                        .eq("id", user_id).execute())
        return raw, prefix

    async def increment_usage(self, user_id: str, n: int) -> None:
        await self._run(lambda: self.client.rpc(
            "increment_usage", {"p_user_id": user_id, "p_n": n}).execute())

    async def reset_running_jobs(self) -> int:
        try:
            res = await self._run(lambda: self.client.table("jobs")
                                  .update({"status": "queued", "started_at": None})
                                  .eq("status", "running").execute())
            return len(res.data or [])
        except Exception as e:
            logger.warning("Could not reset running jobs from Supabase: %s", e)
            return 0
