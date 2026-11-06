"""Module 04: remember the failures of the last run and re-run only those."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from common import make_project  # noqa: E402
from minirun.runner import Runner  # noqa: E402

BODY = """
    def test_ok():
        assert True


    def test_a():
        assert {a}


    def test_b():
        assert {b}
"""


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        runner = Runner()
        project = str(make_project(Path(tmp) / "proj", {
            "tests/test_x.py": BODY.format(a="1 == 2", b="'a' == 'b'"),
            "tests/test_bad_import.py": "import not_a_real_module_zzz\n",
        }))

        try:
            runner.rerun_failed(project)
        except LookupError as e:
            print("ok  rerun before any run is an explained error:", e)
        else:
            raise AssertionError("should have refused")

        first = runner.run(project)
        assert first["summary"]["failed"] == 2 and first["summary"]["passed"] == 1
        assert first["summary"]["collection_errors"] == 1
        assert runner.last_failed[project] == [
            "tests/test_x.py::test_a", "tests/test_x.py::test_b", "tests/test_bad_import.py"]

        # Re-run: only those three ids are passed to pytest, so test_ok is not run.
        second = runner.rerun_failed(project)
        assert second["summary"]["total"] == 2 and second["summary"]["passed"] == 0
        assert second["summary"]["collection_errors"] == 1
        print("ok  rerun ran only the failures (total 2, not 3)")

        # "Fix" test_a and the import; only test_b should be left.
        Path(project, "tests", "test_x.py").write_text(
            dedent(BODY.format(a="1 == 1", b="'a' == 'b'")).lstrip("\n"),
            encoding="utf-8", newline="\n")
        Path(project, "tests", "test_bad_import.py").unlink()
        third = runner.rerun_failed(project)
        assert third["summary"]["total"] == 2 and third["summary"]["passed"] == 1
        assert [f["id"] for f in third["failures"]] == ["tests/test_x.py::test_b"]
        assert runner.last_failed[project] == ["tests/test_x.py::test_b"]
        print("ok  after fixing one, the failure list shrank to", runner.last_failed[project])

        Path(project, "tests", "test_x.py").write_text(
            dedent(BODY.format(a="1 == 1", b="True")).lstrip("\n"),
            encoding="utf-8", newline="\n")
        fourth = runner.rerun_failed(project)
        assert fourth["outcome"] == "passed"
        assert runner.rerun_failed(project) == {"outcome": "nothing_to_rerun"}
        print("ok  all green, then nothing_to_rerun")


if __name__ == "__main__":
    main()
