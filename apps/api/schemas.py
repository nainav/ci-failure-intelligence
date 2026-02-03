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


class TestCaseOut(BaseModel):
    id: int
    nodeid: str
    suite: str | None
    file_path: str | None
    owner: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class TestExecutionOut(BaseModel):
    id: int
    run_id: int
    test_case_id: int
    outcome: str
    duration_sec: float | None
    failure_type: str | None
    error_hash: str | None
    error_message: str | None
    reason_code: str | None
    classified_as: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class IngestResponse(BaseModel):
    run_id: int
    tests_ingested: int