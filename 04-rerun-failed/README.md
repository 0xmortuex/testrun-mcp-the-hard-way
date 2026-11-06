# Module 04: Rerun Failed

## The Concept

The agent's loop is: run everything, see two failures, change code, check those two. Running
the other 2,000 tests each time wastes minutes. pytest has `--lf` ("last failed") for this,
but it depends on a cache directory in the project, and we turned that off on purpose
(`-p no:cacheprovider`, Module 02). So we keep the state ourselves, in memory, and it is more
precise anyway: we know exactly which run the failures came from.

## The state

```python
self.last_failed: dict[str, list[str]] = {}   # project directory -> failing ids
```

Keyed by project, because one server session may test several. After every run:

```python
self.last_failed[project] = [c.id for c in failing] + [c.id for c in collection]
```

Collection errors are included. A file that failed to import has no test ids, but its *path*
is a valid pytest argument and re-running it tells you whether your import fix worked.

## Rerunning

`rerun_failed` passes the remembered ids as pytest arguments, so only those tests run. This is
also why Module 02 insisted on exact node ids: they are the keys that go round-trip. Even the
escaped unicode id `test_param[你好]` works, because it is what pytest printed and
what it accepts.

Three behaviours that a first version gets wrong:

1. **Rerun before any run** is an error with a next step, not an empty success:
   `no earlier run for this project: call run_tests first`.
2. **The list shrinks.** After the rerun, `last_failed` is replaced by what still fails, so
   the next rerun is smaller again. When it is empty the answer is `nothing_to_rerun`, not a
   pytest run with zero arguments (which would run *everything*, the opposite of the
   intent).
3. **Deleted files.** The agent fixes an import error by deleting the broken test file. The
   remembered id points at a file that no longer exists, and pytest answers
   `ERROR: file or directory not found` and runs nothing. `rerun_failed` filters out ids
   whose file is gone before calling pytest.

```python
ids = [i for i in ids if os.path.exists(os.path.join(project, i.split("::", 1)[0]))]
```

There is a cap on the real server (100 ids per rerun) because Windows limits a command line to
about 32,000 characters.

## Run It

```bash
python 04-rerun-failed/main.py
```

The demo runs a three-test project with two failures and an import error, re-runs, "fixes"
one failure and deletes the broken file, re-runs again, and finally makes everything pass.

## What You Learned

- Keep the state you need yourself instead of relying on a side-effect cache.
- Identity (Module 02) is what makes follow-up actions possible.
- Think about what an empty list means before you pass it to a command.

Next: [Module 05](../05-flaky-detection/): when "it passed this time" is not good enough.
