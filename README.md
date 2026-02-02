# CI Failure Intelligence

**Turning CI failures into decisions.**

CI Failure Intelligence is a CI/CD reliability platform that ingests test execution data, detects flaky tests, classifies failures, and surfaces actionable insights for engineering teams.

Modern CI pipelines fail often — but not all failures are equal. This project focuses on answering the question every engineer asks after a red pipeline:

> *Is this a real regression, flaky test noise, or infrastructure instability?*

---

## Why This Exists

Most CI systems tell you **that** something failed.  
Very few tell you **why** it failed — or whether it matters.

Common pain points this project addresses:
- Flaky tests that erode trust in CI
- Infrastructure-induced failures mixed with real regressions
- Lack of historical visibility into test stability
- Manual triage and tribal knowledge around failures
- CI dashboards optimized for execution, not decision-making

This platform treats test results as **signals**, not logs.

---

## Core Capabilities

### 1. Test Result Ingestion
- Ingests JUnit XML results from CI pipelines
- Captures metadata: commit SHA, branch, workflow, timestamps
- Normalizes test identifiers for historical tracking

### 2. Flaky Test Detection
- Tracks execution history per test
- Detects outcome instability across runs
- Identifies rerun-pass scenarios as strong flaky signals
- Ranks tests by flake probability and volatility

### 3. Failure Classification
Failures are automatically classified into meaningful categories:

- **Infrastructure Failures**
  - Network timeouts
  - Connection resets
  - Resource exhaustion
  - Environment instability

- **Test Issues**
  - Intermittent assertions
  - UI synchronization failures
  - Fixture/setup instability

- **Product Regressions**
  - Consistent failures on the same commit
  - Reproducible failures across reruns
  - Signal of actual code defects

Classification is rule-based and explainable by design.

### 4. Reliability Insights & Trends
- Pipeline health overview
- Flake rate trends over time
- Failure breakdown by reason
- Identification of newly introduced regressions
- Test-level history and stability timelines

---

## Architecture Overview

flowchart LR
  A[CI Pipeline<br/>(GitHub Actions / Jenkins)] -->|JUnit XML| B[Ingestion API<br/>(FastAPI)]
  A -->|Logs / metadata| B
  B --> C[(PostgreSQL)]
  C --> D[Analyzer<br/>(flake scoring + classification)]
  D --> E[Dashboard<br/>(Streamlit)]
  D --> F[Alerts (optional)<br/>Slack / Email]
