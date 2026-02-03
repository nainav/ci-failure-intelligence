from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from db import Base, engine, get_db
from models import PipelineRun, TestCase, TestExecution
from schemas import (
    RunCreate, RunOut,
    TestCaseOut, TestExecutionOut,
    IngestResponse
)
from junit_parser import parse_junit_xml

app = FastAPI(title="CI Failure Intelligence")

# DEV convenience: create tables automatically.
# In real deployments, replace this with Alembic migrations.
Base.metadata.create_all(bind=engine)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/runs", response_model=RunOut)
def create_run(payload: RunCreate, db: Session = Depends(get_db)):
    run = PipelineRun(**payload.model_dump(exclude_none=True))
    db.add(run)
    db.commit()
    db.refresh(run)
    return run

@app.get("/runs", response_model=list[RunOut])
def list_runs(db: Session = Depends(get_db), limit: int = 25):
    stmt = select(PipelineRun).order_by(PipelineRun.started_at.desc()).limit(limit)
    return list(db.scalars(stmt).all())

def upsert_test_case(db: Session, nodeid: str, suite: str | None, file_path: str | None) -> TestCase:
    existing = db.scalar(select(TestCase).where(TestCase.nodeid == nodeid))
    if existing:
        # Optional: update suite/file_path if missing
        changed = False
        if suite and not existing.suite:
            existing.suite = suite
            changed = True
        if file_path and not existing.file_path:
            existing.file_path = file_path
            changed = True
        if changed:
            db.add(existing)
        return existing

    tc = TestCase(nodeid=nodeid, suite=suite, file_path=file_path)
    db.add(tc)
    db.flush()  # assign id without commit
    return tc


def create_run_if_needed(
    db: Session,
    provider: str | None,
    workflow: str | None,
    repo: str | None,
    branch: str | None,
    commit_sha: str | None,
    run_external_id: str | None,
    status: str | None,
) -> PipelineRun:
    run = PipelineRun(
        provider=provider or "github",
        workflow=workflow,
        repo=repo,
        branch=branch,
        commit_sha=commit_sha,
        run_external_id=run_external_id,
        status=status or "unknown",
    )
    db.add(run)
    db.flush()
    return run


# -------------------------
# Ingestion (Day 3)
# -------------------------
@app.post("/ingest/junit", response_model=IngestResponse)
async def ingest_junit(
    file: UploadFile = File(...),
    # metadata (optional)
    run_id: int | None = Form(default=None),
    provider: str | None = Form(default="github"),
    workflow: str | None = Form(default=None),
    repo: str | None = Form(default=None),
    branch: str | None = Form(default=None),
    commit_sha: str | None = Form(default=None),
    run_external_id: str | None = Form(default=None),
    status: str | None = Form(default="unknown"),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing file")

    xml_bytes = await file.read()
    if not xml_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    # Resolve run
    if run_id is not None:
        run = db.get(PipelineRun, run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"run_id {run_id} not found")
    else:
        run = create_run_if_needed(
            db=db,
            provider=provider,
            workflow=workflow,
            repo=repo,
            branch=branch,
            commit_sha=commit_sha,
            run_external_id=run_external_id,
            status=status,
        )

    # Parse JUnit
    try:
        parsed = parse_junit_xml(xml_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JUnit XML: {e}")

    # Persist: upsert test cases, insert executions
    ingested = 0
    for r in parsed:
        tc = upsert_test_case(db, nodeid=r.nodeid, suite=r.suite, file_path=r.file_path)

        ex = TestExecution(
            run_id=run.id,
            test_case_id=tc.id,
            outcome=r.outcome,
            duration_sec=r.duration_sec,
            failure_type=r.failure_type,
            error_hash=r.error_hash,
            error_message=r.error_message,
        )
        db.add(ex)
        ingested += 1

    db.commit()
    return IngestResponse(run_id=run.id, tests_ingested=ingested)


# -------------------------
# Listing endpoints (Day 3 verification)
# -------------------------
@app.get("/tests", response_model=list[TestCaseOut])
def list_tests(db: Session = Depends(get_db), limit: int = 50):
    stmt = select(TestCase).order_by(TestCase.created_at.desc()).limit(limit)
    return list(db.scalars(stmt).all())


@app.get("/executions", response_model=list[TestExecutionOut])
def list_executions(
    db: Session = Depends(get_db),
    run_id: int | None = None,
    test_case_id: int | None = None,
    limit: int = 100,
):
    stmt = select(TestExecution).order_by(TestExecution.created_at.desc())
    if run_id is not None:
        stmt = stmt.where(TestExecution.run_id == run_id)
    if test_case_id is not None:
        stmt = stmt.where(TestExecution.test_case_id == test_case_id)
    stmt = stmt.limit(limit)
    return list(db.scalars(stmt).all())