from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    String, Integer, DateTime, Float, ForeignKey, Text, UniqueConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base

class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), default="github", nullable=False)  # github/jenkins/etc
    workflow: Mapped[str | None] = mapped_column(String(128))
    repo: Mapped[str | None] = mapped_column(String(256))
    branch: Mapped[str | None] = mapped_column(String(128))
    commit_sha: Mapped[str | None] = mapped_column(String(64), index=True)
    run_external_id: Mapped[str | None] = mapped_column(String(128), index=True)  # e.g., GHA run_id
    status: Mapped[str] = mapped_column(String(24), default="unknown", nullable=False)  # success/failure/cancelled
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)

    executions: Mapped[list[TestExecution]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_runs_branch_started", "branch", "started_at"),
    )


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # "nodeid" should be stable across runs: e.g., tests/test_api.py::test_login[param]
    nodeid: Mapped[str] = mapped_column(String(512), nullable=False)
    suite: Mapped[str | None] = mapped_column(String(128))
    file_path: Mapped[str | None] = mapped_column(String(256))
    owner: Mapped[str | None] = mapped_column(String(128))  # optional: team/owner tag

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    executions: Mapped[list[TestExecution]] = relationship(
        back_populates="test_case", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("nodeid", name="uq_testcase_nodeid"),
        Index("idx_testcases_suite", "suite"),
    )


class TestExecution(Base):
    __tablename__ = "test_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    run_id: Mapped[int] = mapped_column(ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False)
    test_case_id: Mapped[int] = mapped_column(ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False)

    outcome: Mapped[str] = mapped_column(String(16), nullable=False)  # passed/failed/skipped/error
    duration_sec: Mapped[float | None] = mapped_column(Float)

    # For grouping similar failures across runs
    error_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    failure_type: Mapped[str | None] = mapped_column(String(24))  # assertion/error/timeout/etc

    # Classification output (week 3, but store now)
    reason_code: Mapped[str | None] = mapped_column(String(64), index=True)  # INFRA_TIMEOUT, REGRESSION_ASSERT, etc
    classified_as: Mapped[str | None] = mapped_column(String(24), index=True)  # infra/test/regression

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    run: Mapped[PipelineRun] = relationship(back_populates="executions")
    test_case: Mapped[TestCase] = relationship(back_populates="executions")

    __table_args__ = (
        Index("idx_exec_run_test", "run_id", "test_case_id"),
        Index("idx_exec_test_created", "test_case_id", "created_at"),
    )
