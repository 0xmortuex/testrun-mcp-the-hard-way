# testrun-mcp — The Hard Way

Build an MCP server that lets an AI agent run your tests and understand the result. Start
from `subprocess.Popen` and end with a server an agent can call over stdio. No test-runner
framework hiding what happens, every line explained.

At the end you will have built a minimal version of
[testrun-mcp](https://github.com/0xmortuex/testrun-mcp) yourself, and you will understand the
things most "run a command from an agent" tutorials skip: **how to run untrusted code without
leaking processes**, **how to shrink a 5,000-line log into five useful lines**, and **how to
test a tool whose whole job is to survive misbehaving programs**.

## Why This Exists

An agent that fixes bugs runs the tests dozens of times. Handing it the raw output of
`pytest` is the obvious first version, and it fails in predictable ways:

- the log is enormous, and the one line that matters is in the middle;
- a test hangs and the agent's tool call hangs with it;
- the test started a server, the run timed out, and the server is still there an hour later;
- an import error in one file looks like "the tests failed" and sends the agent to fix the
  wrong thing;
- a flaky test passes on the re-run and the agent decides the bug is fixed.

Every module below is one of those problems, solved and then proven against a real process.

## Who This Is For

- Developers who have written a "hello world" MCP server and want to wrap something real
- Anyone who has been bitten by an orphaned child process after a timeout
- Anyone building a tool that runs code they did not write

**Prerequisites:** Python 3.10+ and comfort with `subprocess`. Nothing else: the projects
under test are built on the fly in temporary directories.

```
python -m venv .venv && .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python verify.py
```

## Modules

| # | Module | What You'll Build |
|---|--------|-------------------|
| 01 | [Running Subprocesses Safely](01-running-subprocesses-safely/) | No shell, closed stdin, a hard timeout, a kill that reaches the whole process tree, bounded output, a scrubbed environment |
| 02 | [JUnit XML Parsing](02-junit-xml-parsing/) | Run pytest with `--junitxml` and turn the XML into exact test ids, counts, and collection errors kept apart |
| 03 | [Trimming Tracebacks](03-trimming-tracebacks/) | Parse `--tb=short`, drop library frames, keep the failing line, clip the noise |
| 04 | [Rerun Failed](04-rerun-failed/) | Remember what failed, re-run only that, and survive a file that no longer exists |
| 05 | [Flaky Detection](05-flaky-detection/) | Run one test N times in fresh processes and read the pattern |
| 06 | [The MCP Wrapper](06-the-mcp-wrapper/) | Three tools, worker threads, errors that reach the agent, tested over real stdio |
| 07 | [Testing a Test Runner](07-testing-a-test-runner/) | Projects built to hurt it: hangs, crashes, import errors, huge output, leaked processes |

Each module contains:
- **`README.md`**: the problem, the design decision, and a walk through the code
- **`main.py`**: runs the code from `minirun/` against real processes and checks the results with `assert`
- **`break-it.md`**: challenges that break your own code, with hints

## How the Code Is Laid Out

The server grows one file per module in [`minirun/`](minirun/):

```
minirun/procs.py    Module 01   run a command safely
minirun/junit.py    Module 02   JUnit XML -> test cases
minirun/trim.py     Module 03   tracebacks -> the frames that matter
minirun/runner.py   Module 02+04  run pytest, parse, remember failures, rerun
minirun/flaky.py    Module 05   N runs -> pattern and verdict
minirun/server.py   Module 06   the MCP tools
```

The module READMEs show the interesting parts of each file and explain the choices; the files
are the finished versions, so a module's `main.py` may use a helper that a later module
refined. Each `main.py` is self-contained apart from importing `minirun` and
[`common.py`](common.py) (temporary projects, "is this pid dead").

## Every Module Is Verified

```bash
python verify.py
```

This runs each module's `main.py`, which builds throwaway projects and runs real pytest,
real processes and (in Module 06) a real MCP session over stdio against them. CI runs it on
Linux and Windows on every push and weekly, so the code in this course cannot silently stop
working.

## Architecture Overview

```
 AI agent (Claude Code, ...)
        |  MCP over stdio: run_tests / rerun_failed / flaky_check     <- Module 06
        v
 +---------------------------------------------------------+
 | server.py   worker thread, errors -> ToolError            |
 |   runner.py   build argv, parse, remember failures        | <- Module 02, 04
 |     junit.py    XML -> cases with exact node ids          | <- Module 02
 |     trim.py     traceback -> relevant frames              | <- Module 03
 |     procs.py    Popen, timeout, tree kill, caps, env      | <- Module 01
 +---------------------------------------------------------+
        |  argv list, no shell, stdin closed
        v
   python -m pytest --junitxml=...        (the project's code runs here)
```

## Key Design Principles

**1. The agent can only act on what you show it.** A 200-line traceback hides the one frame
that matters. `src/cart.py:27 in total` is the whole answer.

**2. Never trust the thing you run.** It will hang, print a gigabyte, read stdin, start
children, and call `os._exit`. Every one of those is a normal Tuesday for a test suite.

**3. "Passed" must mean the tests ran.** No tests collected, a broken `conftest.py` and a
crashed interpreter are three different results, and none of them is a pass.

**4. Errors are instructions.** "pytest not found" is a dead end. "pytest is not installed
for C:\\proj\\.venv\\Scripts\\python.exe; pass python=..." is the next step.

**5. Prove the dangerous part.** The tree kill is only real if a test shows the grandchild
is dead. Module 01 and 07 do exactly that.

MIT licensed.
