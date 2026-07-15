from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class FieldSpec(BaseModel):
    selector: str
    attr: Optional[str] = None


class JobCreate(BaseModel):
    urls: List[str] = Field(min_length=1, max_length=200)
    mode: Literal["auto", "custom"] = "auto"
    fields: Optional[Dict[str, FieldSpec]] = None
    concurrency: int = Field(default=5, ge=1, le=20)
    rate_per_minute: float = Field(default=60.0, gt=0)
    use_browser_fallback: bool = True

    @model_validator(mode="after")
    def _check_custom(self) -> "JobCreate":
        if self.mode == "custom" and not self.fields:
            raise ValueError("custom mode requires at least one field")
        return self


class JobOut(BaseModel):
    id: str
    status: str
    total: int
    completed: int
    failed: int
    error: Optional[str] = None
    config: Dict[str, Any]
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


class ResultOut(BaseModel):
    id: str
    job_id: str
    url: str
    data: Optional[Dict[str, Any]] = None
    status: str
    error: Optional[str] = None
    scraped_at: Optional[str] = None


class UsageOut(BaseModel):
    usage_count: int


class KeyOut(BaseModel):
    api_key: str
    prefix: str
