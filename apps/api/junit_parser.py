from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ParsedTestResult:
    nodeid: str
    suite: str | None
    file_path: str | None
    outcome: str  # passed/failed/skipped/error
    duration_sec: float | None
    failure_type: str | None
    error_message: str | None
    error_hash: str | None


def _hash_error(msg: str) -> str:
    # Stable hash for grouping similar failures
    return hashlib.sha256(msg.encode("utf-8", errors="ignore")).hexdigest()[:32]


def parse_junit_xml(xml_bytes: bytes) -> list[ParsedTestResult]:
    """
    Minimal JUnit XML parser compatible with pytest --junitxml output.
    Handles:
      - <testcase classname="..." name="..." time="...">
      - optional <failure>, <error>, <skipped>
    """
    root = ET.fromstring(xml_bytes)

    # JUnit can have <testsuites> -> <testsuite> -> <testcase>
    # or directly <testsuite> -> <testcase>
    testcases = list(root.iter("testcase"))

    results: list[ParsedTestResult] = []

    for tc in testcases:
        classname = tc.attrib.get("classname", "")
        name = tc.attrib.get("name", "")

        # Build a stable-ish nodeid:
        # pytest often uses classname like "tests.test_api" and name like "test_login[param]"
        # We'll combine them.
        nodeid = f"{classname}::{name}".strip(":")
        suite = classname.split(".")[0] if classname else None
        file_path = classname.replace(".", "/") + ".py" if classname else None

        time_str = tc.attrib.get("time")
        duration = float(time_str) if time_str else None

        outcome = "passed"
        failure_type = None
        error_message = None
        error_hash = None

        # JUnit child tags: failure/error/skipped
        failure = tc.find("failure")
        error = tc.find("error")
        skipped = tc.find("skipped")

        if skipped is not None:
            outcome = "skipped"
            msg = skipped.attrib.get("message") or (skipped.text or "").strip()
            error_message = msg or None
            if error_message:
                error_hash = _hash_error(error_message)

        elif failure is not None:
            outcome = "failed"
            failure_type = "failure"
            msg = failure.attrib.get("message") or (failure.text or "").strip()
            error_message = msg or None
            if error_message:
                error_hash = _hash_error(error_message)

        elif error is not None:
            outcome = "error"
            failure_type = "error"
            msg = error.attrib.get("message") or (error.text or "").strip()
            error_message = msg or None
            if error_message:
                error_hash = _hash_error(error_message)

        results.append(
            ParsedTestResult(
                nodeid=nodeid,
                suite=suite,
                file_path=file_path,
                outcome=outcome,
                duration_sec=duration,
                failure_type=failure_type,
                error_message=error_message,
                error_hash=error_hash,
            )
        )

    return results
