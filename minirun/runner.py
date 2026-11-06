"""Modules 02 and 04: run pytest, parse the XML, remember what failed."""

from __future__ import annotations

import os
import re
import sys
import tempfile
from typing import Any

from . import procs
from .junit import Case, parse_junit
from .trim import clip_tail, parse_traceback, relevant

RESULT_LINE = re.compile(r"^(?P<id>\S.*?::.*?)\s+(?P<res>PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\b")


def running_test(output: str) -> str | None:
    """With -v pytest prints 'tests/test_a.py::test_x ' BEFORE it runs a test and the
    result after. If the output ends on such a half line, that test is the one that hung
    (or killed the process)."""
    lines = [ln for ln in output.splitlines() if ln.strip()]
    if lines and "::" in lines[-1] and not RESULT_LINE.match(lines[-1]):
        return lines[-1].strip()
    return None


def failure_dict(c: Case) -> dict[str, Any]:
    frames, _ = parse_traceback(c.body)
    kept, _dropped = relevant(frames)
    d: dict[str, Any] = {"id": c.id, "message": c.message.splitlines()[0] if c.message else ""}
    if kept:
        d["location"] = f"{kept[-1].file}:{kept[-1].line}"
        d["frames"] = [{"file": f.file, "line": f.line, "in": f.func, "code": f.code} for f in kept]
    if c.stdout:
        d["stdout"] = clip_tail(c.stdout)
    return d


class Runner:
    def __init__(self, allow_env: tuple[str, ...] = ()) -> None:
        self.allow_env = allow_env
        self.last_failed: dict[str, list[str]] = {}  # project dir -> failing ids

    def run(self, project: str, targets: list[str] | None = None, timeout: float = 120,
            extra: list[str] | None = None) -> dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix="minirun-") as tmp:
            xml = os.path.join(tmp, "report.xml")
            argv = [
                sys.executable, "-m", "pytest", f"--junitxml={xml}",
                "-o", "junit_family=xunit1", "-o", "junit_logging=all", "-p", "no:cacheprovider",
                "--tb=short", "-v", "--continue-on-collection-errors",
                *(extra or []), *(targets or []),
            ]
            res = procs.run(argv, project, procs.scrubbed_env(self.allow_env), timeout)
            if res.timed_out:
                return {"outcome": "timeout", "running_when_stopped": running_test(res.output),
                        "output_tail": clip_tail(res.output, 1000)}
            if not os.path.exists(xml):
                # pytest never got as far as writing a report: bad conftest, usage error, or
                # the process died (os._exit, a segfault).
                kind = "startup_error" if res.returncode in (2, 3, 4) else "crashed"
                return {"outcome": kind, "exit_code": res.returncode,
                        "running_when_stopped": running_test(res.output),
                        "output_tail": clip_tail(res.output, 1000)}
            cases = parse_junit(xml)
        tests = [c for c in cases if not c.collection]
        collection = [c for c in cases if c.collection]
        failing = [c for c in tests if c.outcome in ("failed", "error")]
        counts = {k: sum(1 for c in tests if c.outcome == k)
                  for k in ("passed", "failed", "error", "skipped", "xfailed")}
        self.last_failed[project] = [c.id for c in failing] + [c.id for c in collection]
        outcome = "passed" if not failing and not collection and tests else "failed"
        if not tests and not collection:
            outcome = "no_tests"
        result: dict[str, Any] = {
            "outcome": outcome,
            "summary": {**counts, "total": len(tests), "collection_errors": len(collection)},
        }
        if failing:
            result["failures"] = [failure_dict(c) for c in failing[:20]]
        if collection:
            result["collection_errors"] = [failure_dict(c) for c in collection]
        return result

    def rerun_failed(self, project: str, timeout: float = 120) -> dict[str, Any]:
        ids = self.last_failed.get(project)
        if ids is None:
            raise LookupError("no earlier run for this project: call run_tests first")
        # A failing file may have been deleted or renamed since: pytest would answer
        # "file or directory not found" and run nothing. Drop those ids instead.
        ids = [i for i in ids if os.path.exists(os.path.join(project, i.split("::", 1)[0]))]
        if not ids:
            self.last_failed[project] = []
            return {"outcome": "nothing_to_rerun"}
        return self.run(project, ids, timeout)
