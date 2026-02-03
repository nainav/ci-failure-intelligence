from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from db import Base, engine, get_db
from models import PipelineRun
from schemas import RunCreate, RunOut

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
