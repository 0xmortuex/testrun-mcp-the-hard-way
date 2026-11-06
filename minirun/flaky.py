"""Module 05: is this test flaky? Run it N times and look at the pattern."""

from __future__ import annotations

from typing import Any

from .runner import Runner


def flaky_check(runner: Runner, project: str, test_id: str, n: int = 5,
                timeout: float = 60) -> dict[str, Any]:
    if not 2 <= n <= 20:
        raise ValueError("n must be between 2 and 20")
    pattern = ""
    first_failure: dict[str, Any] | None = None
    for _ in range(n):
        # Each run is a brand-new process: nothing carries over inside pytest.
        r = runner.run(project, [test_id], timeout)
        if r["outcome"] == "timeout":
            pattern += "T"
        elif r["outcome"] in ("startup_error", "crashed", "no_tests"):
            raise RuntimeError(f"cannot check {test_id!r}: {r['outcome']}")
        elif r["outcome"] == "passed":
            pattern += "P"
        else:
            pattern += "F"
            if first_failure is None:
                first_failure = (r.get("failures") or [{}])[0]
    bad = n - pattern.count("P")
    if bad == 0:
        verdict = "stable_pass"
    elif bad == n:
        verdict = "consistently_failing"
    else:
        verdict = "flaky"
    out: dict[str, Any] = {"test_id": test_id, "pattern": pattern, "verdict": verdict}
    if verdict == "flaky":
        out["failure_rate"] = round(bad / n, 2)
    if first_failure:
        out["first_failure"] = first_failure
    return out
