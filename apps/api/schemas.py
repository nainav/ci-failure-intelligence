from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel
from pydantic.config import ConfigDict


class RunCreate(BaseModel):
    provider: str = "github"
    workflow: str | None = None
    repo: str | None = None
    branch: str | None = None
    commit_sha: str | None = None
    run_external_id: str | None = None
    status: str = "unknown"
    started_at: datetime | None = None
    finished_at: datetime | None = None


class RunOut(BaseModel):
    id: int
    provider: str
    workflow: str | None
    repo: str | None
    branch: str | None
    commit_sha: str | None
    run_external_id: str | None
    status: str
    started_at: datetime
    finished_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
