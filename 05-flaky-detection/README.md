# Module 05: Flaky Detection

## The Concept

The agent changes a line, re-runs the failing test, and it passes. Is the bug fixed? If the
test is flaky, it might pass 6 times in 10 without any change at all. An agent that cannot
tell the difference will report success that is partly luck, or "fix" a test that was never
broken.

`flaky_check(test_id, n)` runs one test `n` times and looks at the **pattern**:

```
PPFPP   -> flaky: 1 failure in 5, rate 0.2
PPPPP   -> stable_pass
FFFFF   -> consistently_failing
```

[`minirun/flaky.py`](../minirun/flaky.py) is 40 lines.

## Fresh process every time

Each run is a brand-new `pytest` process. Not a loop inside one session: pytest caches
imports, fixtures and module state, and a test that depends on global state would behave
identically on every iteration inside one process and hide the very flakiness we are looking
for. Fresh processes cost a second or two each, which is why `n` is capped at 20 and the
tool description says the worst case is `n x timeout`.

## Making flakiness testable

A test of a flakiness detector needs a test that is flaky *on a schedule you control*.
Randomness would make our own test flaky, which would be embarrassing. The demo uses a counter
file outside the project:

```python
def test_flaky():
    n = int(COUNTER.read_text()) if COUNTER.exists() else 0
    COUNTER.write_text(str(n + 1))
    assert n % 2 == 0, "failed on odd run %d" % n
```

Each fresh process reads how many came before and fails on every odd one, so five runs
produce exactly `PFPFP`. The assertion in `main.py` is on the exact string. This
trick (state in a file, passes decided by a counter) is how you test anything non-deterministic.

## Edge cases that matter

- **A wrong id must not look stable.** If the id matches nothing, pytest collects zero tests,
  exits with code 5, and "no failures" is the same as "passed" to a careless loop. `flaky_check`
  treats `no_tests`, `startup_error` and `crashed` as errors, not as `P`.
- **A timeout is a result.** A test that hangs one time in five is flaky in the worst way.
  It is recorded as `T`, and counts as "not a pass".
- **The first failure is returned.** The reason it failed once is what the agent needs next.
- **What it cannot tell you.** A test that is only flaky when it runs *after* another test, or
  in parallel, will pass here, because it runs alone. The real server's result says so.

## Run It

```bash
python 05-flaky-detection/main.py
```

## What You Learned

- One pass proves little; a pattern over independent runs proves more.
- Test non-determinism by making it deterministic and external.
- Make the "nothing happened" case an error, never a pass.

Next: [Module 06](../06-the-mcp-wrapper/): giving all of this to an agent.
