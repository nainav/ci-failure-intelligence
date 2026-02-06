import os
import requests
import pandas as pd
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="CI Failure Intelligence", layout="wide")

st.title("CI Failure Intelligence")
st.caption("Turning CI failures into decisions (flake vs infra vs regression).")

@st.cache_data(ttl=10)
def fetch_json(path: str):
    r = requests.get(f"{API_URL}{path}", timeout=10)
    r.raise_for_status()
    return r.json()

def safe_df(data):
    if not data:
        return pd.DataFrame()
    return pd.DataFrame(data)

# ---- Top-level metrics ----
runs = fetch_json("/runs?limit=50")
runs_df = safe_df(runs)

executions = fetch_json("/executions?limit=500")
exec_df = safe_df(executions)

col1, col2, col3, col4 = st.columns(4)

total_runs = len(runs_df) if not runs_df.empty else 0
total_exec = len(exec_df) if not exec_df.empty else 0

passed = (exec_df["outcome"] == "passed").sum() if "outcome" in exec_df else 0
failed = (exec_df["outcome"] == "failed").sum() if "outcome" in exec_df else 0
skipped = (exec_df["outcome"] == "skipped").sum() if "outcome" in exec_df else 0
errored = (exec_df["outcome"] == "error").sum() if "outcome" in exec_df else 0

pass_rate = round((passed / total_exec) * 100, 1) if total_exec else 0.0
fail_rate = round(((failed + errored) / total_exec) * 100, 1) if total_exec else 0.0

col1.metric("Runs (last 50)", total_runs)
col2.metric("Executions (last 500)", total_exec)
col3.metric("Pass rate", f"{pass_rate}%")
col4.metric("Fail/Error rate", f"{fail_rate}%")

st.divider()

# ---- Runs table ----
st.subheader("Recent Pipeline Runs")
if runs_df.empty:
    st.info("No runs yet. Trigger GitHub Actions or ingest a local JUnit XML.")
else:
    show_cols = ["id", "provider", "workflow", "repo", "branch", "commit_sha", "run_external_id", "status", "started_at"]
    show_cols = [c for c in show_cols if c in runs_df.columns]
    st.dataframe(runs_df[show_cols], use_container_width=True, height=280)

st.divider()

# ---- Failures ----
st.subheader("Latest Failures (triage view)")

if exec_df.empty:
    st.info("No executions yet. Ingest a JUnit XML to populate data.")
else:
    failures = exec_df[exec_df["outcome"].isin(["failed", "error"])].copy()
    if failures.empty:
        st.success("No failures in the last 500 executions.")
    else:
        # Group top failing test_case_id
        top = (
            failures.groupby("test_case_id")
            .size()
            .reset_index(name="failure_count")
            .sort_values("failure_count", ascending=False)
            .head(10)
        )

        left, right = st.columns([1, 2])

        with left:
            st.markdown("**Top failing tests (by count)**")
            st.dataframe(top, use_container_width=True, height=300)

        with right:
            st.markdown("**Most recent failures**")
            show_cols = ["id", "run_id", "test_case_id", "outcome", "failure_type", "error_hash", "created_at"]
            show_cols = [c for c in show_cols if c in failures.columns]
            st.dataframe(failures.sort_values("created_at", ascending=False)[show_cols].head(25),
                         use_container_width=True, height=300)

st.divider()
st.divider()
st.subheader("Flaky Test Leaderboard")

flakes = fetch_json("/flakes")
flakes_df = safe_df(flakes)

if flakes_df.empty:
    st.info("No flaky tests detected yet. Run CI a few more times.")
else:
    st.dataframe(
        flakes_df,
        use_container_width=True,
        height=300
    )

    st.caption(
        "Flake score = outcome changes / (executions - 1). "
        "Higher score means more unstable."
    )

# ---- Drilldown: executions by run ----
st.subheader("Drilldown: Executions by Run")
if runs_df.empty:
    st.info("No runs available.")
else:
    run_ids = runs_df["id"].tolist()
    selected_run = st.selectbox("Select run_id", run_ids)
    run_exec = fetch_json(f"/executions?run_id={selected_run}&limit=500")
    run_exec_df = safe_df(run_exec)

    if run_exec_df.empty:
        st.warning("No executions for this run.")
    else:
        # outcome breakdown
        counts = run_exec_df["outcome"].value_counts().reset_index()
        counts.columns = ["outcome", "count"]
        st.dataframe(counts, use_container_width=True)

        st.dataframe(
            run_exec_df.sort_values("created_at", ascending=False)[
                [c for c in ["id","test_case_id","outcome","duration_sec","failure_type","error_hash","created_at"] if c in run_exec_df.columns]
            ],
            use_container_width=True,
            height=320,
        )

st.caption(f"API: {API_URL} • Refreshes every 10s")
