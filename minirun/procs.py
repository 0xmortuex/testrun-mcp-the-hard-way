"""Module 01: run a command safely.

Five promises, each one a line or two below:
  1. no shell                      (argv list, shell=False)
  2. stdin is closed               (stdin=DEVNULL)
  3. it cannot run forever         (timeout, then kill)
  4. the kill reaches the whole process TREE
  5. a talkative child cannot eat our memory (keep only the head and the tail)
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any

HEAD_BYTES = 8 * 1024
TAIL_BYTES = 24 * 1024

# Variables a test process needs just to start. Everything else (API keys,
# tokens) is dropped unless the caller allows it by name.
BASE_ENV = {
    "PATH", "PATHEXT", "SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "COMSPEC", "TEMP", "TMP",
    "TMPDIR", "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "LANG", "LC_ALL", "TZ",
}


def scrubbed_env(allow: tuple[str, ...] = ()) -> dict[str, str]:
    keep = BASE_ENV | {a.upper() for a in allow}
    env = {k: v for k, v in os.environ.items() if k.upper() in keep}
    env["PYTHONUNBUFFERED"] = "1"  # so a hung test's last line is visible
    env["PYTHONIOENCODING"] = "utf-8"
    return env


@dataclass
class Result:
    returncode: int | None  # None when we had to kill it
    timed_out: bool
    output: str
    seconds: float
    dropped_bytes: int


class _Capture:
    """Keep the first HEAD_BYTES and the last TAIL_BYTES; count what was dropped."""

    def __init__(self) -> None:
        self.head = bytearray()
        self.tail = bytearray()
        self.total = 0

    def feed(self, chunk: bytes) -> None:
        self.total += len(chunk)
        room = HEAD_BYTES - len(self.head)
        if room > 0:
            self.head += chunk[:room]
            chunk = chunk[room:]
        self.tail += chunk
        del self.tail[: max(0, len(self.tail) - TAIL_BYTES)]


# --- killing a whole tree -----------------------------------------------------
# Killing only the child leaves its children running. A test that starts a dev
# server would leak it on every timeout. The two platforms solve this differently.

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    class _Basic(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class _Io(ctypes.Structure):
        _fields_ = [(n, ctypes.c_uint64) for n in (
            "ReadOps", "WriteOps", "OtherOps", "ReadBytes", "WriteBytes", "OtherBytes")]

    class _Extended(ctypes.Structure):
        _fields_ = [
            ("Basic", _Basic), ("Io", _Io), ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _k32.CreateJobObjectW.restype = wintypes.HANDLE
    _k32.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
    _k32.SetInformationJobObject.argtypes = [
        wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
    _k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    _k32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    _k32.CloseHandle.argtypes = [wintypes.HANDLE]


class TreeKiller:
    """Windows: a Job Object. Every process the child starts joins the job, and
    TerminateJobObject kills them all, even ones whose parent already exited.
    POSIX: a new session, so the child leads its own process group; killpg hits the group."""

    def __init__(self, proc: subprocess.Popen[bytes]) -> None:
        self.proc = proc
        self.job: Any = None
        if sys.platform == "win32":
            job = _k32.CreateJobObjectW(None, None)
            info = _Extended()
            info.Basic.LimitFlags = 0x2000  # KILL_ON_JOB_CLOSE: if we die, they die
            _k32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info))
            if not _k32.AssignProcessToJobObject(job, int(proc._handle)):  # type: ignore[attr-defined]
                raise OSError(ctypes.get_last_error(), "AssignProcessToJobObject failed")
            self.job = job

    def kill(self) -> None:
        if sys.platform == "win32":
            if self.job:
                _k32.TerminateJobObject(self.job, 1)
        else:
            try:
                os.killpg(self.proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass  # nobody left in the group

    def close(self) -> None:
        if sys.platform == "win32" and self.job:
            _k32.CloseHandle(self.job)
            self.job = None


def _pump(stream: Any, cap: _Capture) -> None:
    try:
        while True:
            chunk = stream.read1(65536)
            if not chunk:
                return
            cap.feed(chunk)
    except (OSError, ValueError):
        return


def run(argv: list[str], cwd: str, env: dict[str, str], timeout: float) -> Result:
    kwargs: dict[str, Any] = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    else:
        kwargs["start_new_session"] = True  # own process group
    start = time.monotonic()
    proc = subprocess.Popen(
        argv, cwd=cwd, env=env,
        shell=False,                    # promise 1
        stdin=subprocess.DEVNULL,       # promise 2
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        **kwargs,
    )
    killer = TreeKiller(proc)
    cap = _Capture()
    assert proc.stdout is not None
    reader = threading.Thread(target=_pump, args=(proc.stdout, cap), daemon=True)
    reader.start()
    timed_out = False
    try:
        try:
            proc.wait(timeout=timeout)          # promise 3
        except subprocess.TimeoutExpired:
            timed_out = True
            killer.kill()                       # promise 4
            proc.wait()
        reader.join(2.0)
        # Sweep even after a clean exit: a test may have left a daemon behind.
        killer.kill()
        reader.join(2.0)
    finally:
        killer.close()
        proc.stdout.close()
    head = bytes(cap.head).decode("utf-8", errors="replace")
    tail = bytes(cap.tail).decode("utf-8", errors="replace")
    dropped = cap.total - len(cap.head) - len(cap.tail)
    output = head if not tail else head + (f"\n[... {dropped} bytes dropped ...]\n" if dropped else "") + tail
    return Result(None if timed_out else proc.returncode, timed_out, output,
                  time.monotonic() - start, dropped)
