# Module 01: Running Subprocesses Safely

## The Concept

Everything in this course starts with one function: take a command, run it, give back what
it printed. The naive version is one line:

```python
subprocess.run(cmd, shell=True, capture_output=True, timeout=60)
```

and it is wrong in five ways once the command is "the test suite of a project I did not
write". This module fixes them one at a time, in [`minirun/procs.py`](../minirun/procs.py).

## Promise 1: No shell

`shell=True` hands the string to `cmd.exe` or `sh`, which interprets `&`, `;`, `$(...)`,
quotes, globs. If any part of the command comes from an agent, that is a command-injection
hole, and on Windows the quoting rules differ from every other platform. With an argument
list and `shell=False` there is nothing to interpret: each element reaches the program as one
argument, byte for byte.

```python
subprocess.Popen(argv, shell=False, ...)
```

`main.py` passes `"a & echo INJECTED; $(whoami)"` as an argument and checks that the child
prints exactly that string back.

## Promise 2: Stdin is closed

A test that calls `input()` (or a library that prompts for a password) waits forever for a
human who is not there. `stdin=subprocess.DEVNULL` makes the read return EOF immediately.

## Promise 3: It cannot run forever

`Popen.wait(timeout=...)` raises `TimeoutExpired`; we catch it and kill. The timeout belongs
to the *caller of the tool* (default a few minutes), because only the caller knows whether
the suite is supposed to take ten seconds or ten minutes.

## Promise 4: The kill reaches the whole tree

`proc.kill()` kills one process. If the test started a database, a browser, a worker pool,
those keep running, now orphaned and holding ports and files. The two platforms solve this
differently.

**Windows: a Job Object.** A job is a group of processes the OS tracks. Put the child in a
job and every process it starts later is in the job too. `TerminateJobObject` kills them all,
including ones whose parent already exited, which `taskkill /T` (it walks parent links) can
miss. Setting `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` adds a safety net: if *our* process dies,
the OS closes the job handle and kills the tree.

```python
job = CreateJobObjectW(None, None)
info.Basic.LimitFlags = 0x2000                       # KILL_ON_JOB_CLOSE
SetInformationJobObject(job, 9, byref(info), sizeof(info))
AssignProcessToJobObject(job, int(proc._handle))     # then: TerminateJobObject(job, 1)
```

This is `ctypes` against `kernel32`, with no third-party dependency (the usual shortcut,
`psutil`, would add one).

**POSIX: a process group.** `start_new_session=True` makes the child a session leader, so
its pid is also its process group id; `os.killpg(pid, SIGKILL)` signals every member. The
limitation is honest: a descendant that calls `setsid()` itself leaves the group. A container
is the only complete answer, and the README of the real server says so.

One more detail: we kill the tree **even after a clean exit**. A test that starts a daemon and
returns normally would otherwise leave it running forever. `main.py` proves both cases by
having the child write the grandchild's pid to a file, then checking, with the OS, that the pid
is gone (`common.wait_dead`).

## Promise 5: Bounded output

A test that prints in a loop can produce gigabytes. We read the pipe in a thread and keep only
the first 8 KiB and the last 24 KiB, counting what we drop:

```python
self.tail += chunk
del self.tail[: max(0, len(self.tail) - TAIL_BYTES)]
```

Head and tail, not just tail: the start has the platform banner and the config, the end has
the summary and the crash. Draining the pipe matters too: if you stop reading, the child
blocks on a full pipe and looks hung.

## Also: a scrubbed environment

The agent's environment may hold API keys. The tests do not need them. `scrubbed_env()` starts
from an empty dictionary and copies only a short list of names a process needs to start
(`PATH`, `HOME`, `SYSTEMROOT`...) plus any the operator allows by name. It also sets
`PYTHONUNBUFFERED=1`; without it a hung Python test's last line is stuck in a buffer and you
cannot tell which test hung (Module 02 uses that line).

## Run It

```bash
python 01-running-subprocesses-safely/main.py
```

Expected output:

```
ok  no shell
ok  stdin closed
ok  timeout after 2.0s
ok  grandchild 17532 died with its parent
ok  orphan 9124 swept after a clean exit
ok  output capped (5167241 bytes dropped, 32801 chars kept)
ok  environment scrubbed, allow-list works
```

## What You Learned

- Argument lists, not shell strings.
- A timeout is only half of a kill; the other half is the tree.
- Prove process behavior with the operating system, not with the code under test.
- Bounded buffers keep a runaway child from becoming your out-of-memory.

Next: [Module 02](../02-junit-xml-parsing/): making sense of what the tests printed.
