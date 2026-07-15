import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol, Tuple

from app.core.apikeys import generate_api_key


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store(Protocol):
    """Persistence interface. FakeStore (tests) and SupabaseStore (production) both
    implement this. All job/result reads are scoped to the owning user_id."""

    async def create_job(self, user_id: str, config: Dict[str, Any], total: int) -> Dict[str, Any]: ...
    async def get_job(self, job_id: str, user_id: str) -> Optional[Dict[str, Any]]: ...
    async def list_jobs(self, user_id: str) -> List[Dict[str, Any]]: ...
    async def set_job_status(self, job_id: str, status: str, error: Optional[str] = None,
                             started: bool = False, finished: bool = False) -> None: ...
    async def bump_job_progress(self, job_id: str, ok: bool) -> None: ...
    async def add_result(self, job_id: str, user_id: str, url: str,
                         data: Optional[Dict[str, Any]], status: str,
                         error: Optional[str] = None) -> Dict[str, Any]: ...
    async def list_results(self, job_id: str, user_id: str) -> List[Dict[str, Any]]: ...
    async def get_profile(self, user_id: str) -> Dict[str, Any]: ...
    async def get_profile_by_api_key_prefix(self, prefix: str) -> Optional[Dict[str, Any]]: ...
    async def rotate_api_key(self, user_id: str) -> Tuple[str, str]: ...
    async def increment_usage(self, user_id: str, n: int) -> None: ...
    async def reset_running_jobs(self) -> int: ...


class FakeStore:
    """In-memory Store implementation used by the test suite."""

    def __init__(self) -> None:
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.results: Dict[str, Dict[str, Any]] = {}
        self.profiles: Dict[str, Dict[str, Any]] = {}
        self._seq = 0

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def _ensure_profile(self, user_id: str) -> Dict[str, Any]:
        prof = self.profiles.get(user_id)
        if prof is None:
            prof = {"id": user_id, "api_key_hash": None, "api_key_prefix": None,
                    "usage_count": 0, "created_at": _now()}
            self.profiles[user_id] = prof
        return prof

    async def create_job(self, user_id: str, config: Dict[str, Any], total: int) -> Dict[str, Any]:
        job = {
            "id": str(uuid.uuid4()), "user_id": user_id, "status": "queued",
            "config": config, "total": total, "completed": 0, "failed": 0,
            "error": None, "created_at": _now(), "started_at": None, "finished_at": None,
            "_seq": self._next_seq(),
        }
        self.jobs[job["id"]] = job
        return dict(job)

    async def get_job(self, job_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        job = self.jobs.get(job_id)
        if job is None or job["user_id"] != user_id:
            return None
        return dict(job)

    async def list_jobs(self, user_id: str) -> List[Dict[str, Any]]:
        owned = [j for j in self.jobs.values() if j["user_id"] == user_id]
        owned.sort(key=lambda j: j["_seq"], reverse=True)
        return [dict(j) for j in owned]

    async def set_job_status(self, job_id: str, status: str, error: Optional[str] = None,
                             started: bool = False, finished: bool = False) -> None:
        job = self.jobs.get(job_id)
        if job is None:
            return
        job["status"] = status
        if error is not None:
            job["error"] = error
        if started:
            job["started_at"] = _now()
        if finished:
            job["finished_at"] = _now()

    async def bump_job_progress(self, job_id: str, ok: bool) -> None:
        job = self.jobs.get(job_id)
        if job is None:
            return
        job["completed" if ok else "failed"] += 1

    async def add_result(self, job_id: str, user_id: str, url: str,
                         data: Optional[Dict[str, Any]], status: str,
                         error: Optional[str] = None) -> Dict[str, Any]:
        res = {
            "id": str(uuid.uuid4()), "job_id": job_id, "user_id": user_id, "url": url,
            "data": data, "status": status, "error": error, "scraped_at": _now(),
            "_seq": self._next_seq(),
        }
        self.results[res["id"]] = res
        return dict(res)

    async def list_results(self, job_id: str, user_id: str) -> List[Dict[str, Any]]:
        owned = [r for r in self.results.values()
                 if r["job_id"] == job_id and r["user_id"] == user_id]
        owned.sort(key=lambda r: r["_seq"])
        return [dict(r) for r in owned]

    async def get_profile(self, user_id: str) -> Dict[str, Any]:
        return dict(self._ensure_profile(user_id))

    async def get_profile_by_api_key_prefix(self, prefix: str) -> Optional[Dict[str, Any]]:
        for prof in self.profiles.values():
            if prof.get("api_key_prefix") == prefix:
                return dict(prof)
        return None

    async def rotate_api_key(self, user_id: str) -> Tuple[str, str]:
        prof = self._ensure_profile(user_id)
        raw, prefix, hashed = generate_api_key()
        prof["api_key_hash"] = hashed
        prof["api_key_prefix"] = prefix
        return raw, prefix

    async def increment_usage(self, user_id: str, n: int) -> None:
        prof = self._ensure_profile(user_id)
        prof["usage_count"] += n

    async def reset_running_jobs(self) -> int:
        count = 0
        for job in self.jobs.values():
            if job["status"] == "running":
                job["status"] = "queued"
                job["started_at"] = None
                count += 1
        return count
