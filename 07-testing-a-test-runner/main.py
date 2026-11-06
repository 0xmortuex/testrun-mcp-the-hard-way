"""Module 07: test the runner against projects built to hurt it."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from common import make_project, wait_dead, wait_for_file  # noqa: E402
from minirun.runner import Runner  # noqa: E402


def project(tmp: str, name: str, files: dict[str, str]) -> str:
    return str(make_project(Path(tmp) / name, files))


def main() -> None:
    runner = Runner()
    with tempfile.TemporaryDirectory() as tmp:
        # 1. A project that is simply fine. The boring case needs an exact assertion too.
        r = runner.run(project(tmp, "green", {"tests/test_ok.py": "def test_a(): pass\n"}))
        assert r["outcome"] == "passed" and r["summary"]["passed"] == 1
        print("ok  green project")

        # 2. No tests at all must not look like success.
        r = runner.run(project(tmp, "empty", {"tests/test_x.py": "x = 1\n"}))
        assert r["outcome"] == "no_tests", r
        print("ok  no tests collected is reported as no_tests")

        # 3. conftest.py that cannot be imported: pytest never writes a report.
        r = runner.run(project(tmp, "badconf", {
            "conftest.py": "import nothing_here_xyz\n", "tests/test_a.py": "def test_a(): pass\n"}))
        assert r["outcome"] == "startup_error" and "nothing_here_xyz" in r["output_tail"]
        print("ok  broken conftest.py is a startup_error with the reason")

        # 4. A test that kills the interpreter. No XML, but we still know who did it.
        r = runner.run(project(tmp, "crash", {"tests/test_c.py": """
            import os


            def test_fine():
                pass


            def test_dies():
                os._exit(7)
        """}))
        assert r["outcome"] == "crashed" and r["exit_code"] == 7
        assert r["running_when_stopped"].startswith("tests/test_c.py::test_dies")
        print("ok  os._exit is a crash, and test_dies is named")

        # 5. A hang, with a child process the test started. The proof that matters:
        #    after the timeout, the grandchild is really gone.
        pidfile = Path(tmp) / "grandchild.pid"
        hang = project(tmp, "hang", {"tests/test_h.py": f"""
            import subprocess, sys, time


            def test_hangs():
                code = "import os, sys, time; open(sys.argv[1], 'w').write(str(os.getpid())); time.sleep(600)"
                subprocess.Popen([sys.executable, "-c", code, {str(pidfile)!r}])
                time.sleep(600)
        """})
        r = runner.run(hang, timeout=15)
        assert r["outcome"] == "timeout"
        assert r["running_when_stopped"].startswith("tests/test_h.py::test_hangs")
        pid = int(wait_for_file(pidfile))
        assert wait_dead(pid), "the test's child process outlived the timeout"
        print(f"ok  hang: killed, test_hangs named, grandchild {pid} dead")

        # 6. Huge output from a passing test and a failing one.
        r = runner.run(project(tmp, "loud", {"tests/test_l.py": """
            def test_loud_fail():
                for i in range(30000):
                    print("noise", i, "x" * 60)
                assert False, "boom"
        """}))
        assert r["outcome"] == "failed"
        out = r["failures"][0]["stdout"]
        assert len(out) < 1600 and out.endswith("noise 29999 " + "x" * 60)
        print("ok  2 MB of output became", len(out), "chars")

        # 7. Secrets in the server's environment must not reach the tests.
        import os

        os.environ["MINIRUN_TEST_SECRET"] = "s3cret"
        r = runner.run(project(tmp, "env", {"tests/test_e.py": """
            import os


            def test_no_secret():
                assert "MINIRUN_TEST_SECRET" not in os.environ
        """}))
        assert r["outcome"] == "passed"
        print("ok  environment was scrubbed")


if __name__ == "__main__":
    main()
