"""Module 01: prove the five promises of minirun.procs.run, against real processes."""

from __future__ import annotations

import os
import sys
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from common import wait_dead, wait_for_file  # noqa: E402
from minirun import procs  # noqa: E402


def py(code: str, timeout: float = 30, args: list[str] | None = None,
       env: dict[str, str] | None = None) -> procs.Result:
    argv = [sys.executable, "-c", textwrap.dedent(code), *(args or [])]
    return procs.run(argv, os.getcwd(), env or dict(os.environ), timeout)


def main() -> None:
    # 1. No shell: shell metacharacters are just characters.
    r = py("import sys; print(sys.argv[1])", args=["a & echo INJECTED; $(whoami)"])
    assert r.output.strip() == "a & echo INJECTED; $(whoami)", r.output
    print("ok  no shell")

    # 2. stdin is closed: a test that calls input() gets EOF instead of hanging.
    r = py("import sys; print(repr(sys.stdin.read()))")
    assert r.output.strip() == "''" and not r.timed_out
    print("ok  stdin closed")

    # 3. A hung process is killed at the timeout.
    r = py("import time; time.sleep(600)", timeout=2)
    assert r.timed_out and r.returncode is None and r.seconds < 15
    print(f"ok  timeout after {r.seconds:.1f}s")

    # 4. The kill reaches grandchildren. The child starts a grandchild that writes its
    #    pid and sleeps; after the timeout that pid must be dead.
    with tempfile.TemporaryDirectory() as tmp:
        pidfile = Path(tmp) / "pid.txt"
        code = """
            import subprocess, sys, time
            sleeper = "import os, sys, time; open(sys.argv[1], 'w').write(str(os.getpid())); time.sleep(600)"
            subprocess.Popen([sys.executable, "-c", sleeper, sys.argv[1]])
            time.sleep(600)
        """
        r = py(code, timeout=8, args=[str(pidfile)])
        pid = int(wait_for_file(pidfile))
        assert r.timed_out
        assert wait_dead(pid), "the grandchild survived the kill!"
        print(f"ok  grandchild {pid} died with its parent")

        # ...and a daemon left behind by a process that EXITED NORMALLY is swept too.
        pidfile2 = Path(tmp) / "pid2.txt"
        code = """
            import subprocess, sys
            sleeper = "import os, sys, time; open(sys.argv[1], 'w').write(str(os.getpid())); time.sleep(600)"
            subprocess.Popen([sys.executable, "-c", sleeper, sys.argv[1]])
        """
        r = py(code, args=[str(pidfile2)])
        assert r.returncode == 0 and not r.timed_out
        pid2 = int(wait_for_file(pidfile2))
        assert wait_dead(pid2), "an orphaned daemon was left running!"
        print(f"ok  orphan {pid2} swept after a clean exit")

    # 5. A chatty child cannot flood us: 5 MB in, a few KB kept.
    r = py("""
        import sys
        for i in range(50000):
            sys.stdout.write("line %06d " % i + "x" * 90 + chr(10))
        print("THE END")
    """)
    assert r.dropped_bytes > 4_000_000
    assert len(r.output) < procs.HEAD_BYTES + procs.TAIL_BYTES + 200
    assert "line 000000" in r.output and "THE END" in r.output and "bytes dropped" in r.output
    print(f"ok  output capped ({r.dropped_bytes} bytes dropped, {len(r.output)} chars kept)")

    # Environment scrubbing: a secret in OUR environment must not reach the child.
    os.environ["MINIRUN_FAKE_SECRET"] = "hunter2"
    r = py("import os; print(os.environ.get('MINIRUN_FAKE_SECRET'))", env=procs.scrubbed_env())
    assert r.output.strip() == "None", r.output
    r = py("import os; print(os.environ.get('MINIRUN_FAKE_SECRET'))",
           env=procs.scrubbed_env(allow=("MINIRUN_FAKE_SECRET",)))
    assert r.output.strip() == "hunter2"
    print("ok  environment scrubbed, allow-list works")


if __name__ == "__main__":
    main()
