"""Module 05: detect a flaky test with a counter file, deterministically."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from common import make_project  # noqa: E402
from minirun.flaky import flaky_check  # noqa: E402
from minirun.runner import Runner  # noqa: E402


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        counter = Path(tmp) / "counter.txt"
        # A "flaky" test needs a source of non-determinism. Real ones use time, threads,
        # randomness or a shared database. Ours uses a counter that lives OUTSIDE the
        # project, so every fresh pytest process sees how many runs came before it.
        project = str(make_project(Path(tmp) / "proj", {
            "tests/test_flaky.py": f"""
                import pathlib

                COUNTER = pathlib.Path({str(counter)!r})


                def test_flaky():
                    n = int(COUNTER.read_text()) if COUNTER.exists() else 0
                    COUNTER.write_text(str(n + 1))
                    assert n % 2 == 0, "failed on odd run %d" % n


                def test_stable():
                    assert True


                def test_broken():
                    assert False
            """,
        }))
        runner = Runner()

        r = flaky_check(runner, project, "tests/test_flaky.py::test_flaky", n=5)
        assert r["pattern"] == "PFPFP", r["pattern"]
        assert r["verdict"] == "flaky" and r["failure_rate"] == 0.4
        assert r["first_failure"]["message"].startswith("AssertionError: failed on odd run 1")
        print("ok  flaky:", r["pattern"], "failure rate", r["failure_rate"])

        r = flaky_check(runner, project, "tests/test_flaky.py::test_stable", n=3)
        assert r["pattern"] == "PPP" and r["verdict"] == "stable_pass"
        r = flaky_check(runner, project, "tests/test_flaky.py::test_broken", n=3)
        assert r["pattern"] == "FFF" and r["verdict"] == "consistently_failing"
        print("ok  stable and consistently failing are told apart from flaky")

        try:
            flaky_check(runner, project, "tests/test_flaky.py::test_nope", n=2)
        except RuntimeError as e:
            print("ok  a wrong id is an error, not a false 'stable':", e)
        else:
            raise AssertionError("an unknown test id must not look like a pass")

        try:
            flaky_check(runner, project, "tests/test_flaky.py::test_stable", n=99)
        except ValueError as e:
            print("ok  n is bounded:", e)
        else:
            raise AssertionError("n must be bounded")


if __name__ == "__main__":
    main()
