"""Module 02: run real pytest on a throwaway project and check the parsed result exactly."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from common import make_project  # noqa: E402
from minirun.junit import node_id  # noqa: E402
from minirun.runner import Runner  # noqa: E402

PROJECT = {
    "tests/test_shapes.py": """
        import pytest


        class TestSquare:
            def test_area(self):
                assert 3 * 3 == 9

            def test_wrong(self):
                print("computing")
                assert 3 * 3 == 10


        @pytest.mark.parametrize("v", ["你好", "ok"])
        def test_param(v):
            assert v == "ok"


        @pytest.mark.skip(reason="not today")
        def test_skipped():
            pass


        def test_error_in_code():
            {}["missing"]
    """,
    "tests/test_broken_import.py": """
        import module_that_does_not_exist
    """,
}


def main() -> None:
    # The id rebuilt from three XML attributes.
    assert node_id("tests\\test_a.py", "tests.test_a.TestX", "test_y[1]") == "tests/test_a.py::TestX::test_y[1]"
    assert node_id("tests/test_a.py", "tests.test_a", "test_f") == "tests/test_a.py::test_f"
    assert node_id("t.py", "t.Outer.Inner", "test_g") == "t.py::Outer::Inner::test_g"
    print("ok  node ids")

    with tempfile.TemporaryDirectory() as tmp:
        project = str(make_project(Path(tmp) / "proj", PROJECT))
        result = Runner().run(project)

    assert result["outcome"] == "failed"
    assert result["summary"] == {
        "passed": 2, "failed": 3, "error": 0, "skipped": 1, "xfailed": 0,
        "total": 6, "collection_errors": 1,
    }, result["summary"]
    assert {f["id"] for f in result["failures"]} == {
        "tests/test_shapes.py::TestSquare::test_wrong",
        "tests/test_shapes.py::test_param[\\u4f60\\u597d]",  # pytest escapes non-ASCII ids
        "tests/test_shapes.py::test_error_in_code",
    }, [f["id"] for f in result["failures"]]
    by_id = {f["id"]: f for f in result["failures"]}
    wrong = by_id["tests/test_shapes.py::TestSquare::test_wrong"]
    assert wrong["stdout"] == "computing"
    assert "3 * 3" in wrong["message"] and "10" in wrong["message"], wrong["message"]
    # A collection error is NOT listed among the failures:
    assert [c["id"] for c in result["collection_errors"]] == ["tests/test_broken_import.py"]
    print("ok  counts, ids and the collection error are exact")
    print(f"    failures: {sorted(by_id)}")


if __name__ == "__main__":
    main()
