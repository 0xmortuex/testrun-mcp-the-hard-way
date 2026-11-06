# Module 07: Testing a Test Runner

## The Concept

A test runner's reason to exist is to survive code that misbehaves. So its own tests cannot
use well-behaved fixtures. You have to **build the misbehaving projects**, run the real thing
against them, and assert on exact results.

The temptation is to mock: patch `subprocess.run`, return canned XML, check the parsing. That
tests your parser against what you *think* pytest writes. It would not have caught that
`junit_family=xunit1` is needed for the `file=` attribute (Module 02), that a module calling
`sys.exit()` at import makes pytest itself crash with exit code 3, or that on Windows the
paths come back with backslashes. Real tools told us all three.

## One project per failure mode

[`main.py`](main.py) creates each project in a temporary directory with `common.make_project`
(explicit UTF-8, explicit `\n` line endings, so CRLF/LF and locale cannot change a result):

| Project | What it does | The exact assertion |
|---|---|---|
| green | one passing test | `outcome == "passed"` |
| empty | a test file with no tests | `outcome == "no_tests"`, never "passed" |
| badconf | `conftest.py` imports a missing module | `startup_error`, and the module name is in the output tail |
| crash | a test calls `os._exit(7)` | `crashed`, `exit_code == 7`, and **the dying test is named** |
| hang | a test sleeps forever after starting a child | `timeout`, the test is named, and the child is dead |
| loud | a failing test prints 30,000 lines | the failure's stdout is under 1,600 chars and ends with the last line |
| env | a test asserts a secret is absent | `passed` |

## Proving a negative with the OS

"The child process is dead" is a claim about the operating system, not about your code. The
test therefore asks the OS:

```python
pid = int(wait_for_file(pidfile))     # the grandchild wrote its own pid
assert wait_dead(pid)                 # Windows: GetExitCodeProcess; POSIX: ps -o stat=
```

Two details make this test honest:

- `wait_for_file` polls instead of sleeping a fixed time. A slow CI machine may start the
  grandchild late; a fixed sleep would turn that into a false alarm.
- On POSIX a killed process can linger as a *zombie* until its parent reaps it. A zombie is
  dead; `wait_dead` treats state `Z` as dead. Using `os.kill(pid, 0)` would call it alive and
  produce a test that fails only in some containers.

## Naming the test that hung

When pytest is run with `-v` it prints `tests/test_h.py::test_hangs ` *before* running the
test and ` PASSED` after. If the output ends on a half-written line, that test is the one that
did not finish:

```python
if lines and "::" in lines[-1] and not RESULT_LINE.match(lines[-1]):
    return lines[-1].strip()
```

This only works because Module 01 set `PYTHONUNBUFFERED=1`. Without it the half line is stuck
in the child's buffer when we kill it. A timeout that says "something hung" is a shrug; one
that says "`test_hangs` hung" is a bug report.

## Lessons from running this on three operating systems

- Make expectations independent of the machine: set `user.name` if you call `git`, set
  encodings explicitly, never rely on the default locale or on `HOME`.
- Do not scan the whole machine in a test ("is any process using this port?"). Ask about the
  one thing you created.
- Timeouts in tests need slack: a hang test with a 4-second limit passes on your laptop and
  flakes on a loaded macOS runner, because pytest took 3 seconds to start. Use a generous limit
  and assert on *behavior*, not on how quickly it happened.
- Keep every test project in `tmp`; clean up is the temp directory's job.

## Run It

```bash
python 07-testing-a-test-runner/main.py
python verify.py        # all seven modules, the way CI runs them
```

## What You Learned

- Build projects that hurt the tool, run the real tools, and assert on exact results.
- Verify process facts with the operating system, and poll instead of sleeping.
- A good failure result names the culprit.

## Where to Go Next

The finished version of this server is
[testrun-mcp](https://github.com/0xmortuex/testrun-mcp). On top of what you built it adds
unittest, jest and vitest; `explain_failure` with local variables; coverage; a `--dir`
sandbox; an allow-list for extra arguments; interpreter detection; and a test suite that
includes real jest and real vitest.
