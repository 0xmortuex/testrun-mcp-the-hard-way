# Break It: Running Subprocesses Safely

## Challenge 1: Kill Only the Child

In `TreeKiller.kill`, replace the body with `self.proc.kill()` and run `main.py`.
Which assertion fails, and why does it fail on both Windows and Linux?

**Hint:** `Popen.kill` signals one pid. The grandchild is not that pid. The "grandchild died
with its parent" check reads the grandchild's pid from a file and asks the OS about it.

## Challenge 2: Stop Draining the Pipe

Make `_pump` read only the first 1 KiB and return. Run the "output capped" check with a child
that prints 5 MB.

**Hint:** The child blocks on a full pipe (about 64 KiB on Linux, 4 KiB on Windows) and never
exits. You will see the timeout fire, not a clean exit. A quiet reader looks exactly like a
hung child.

## Challenge 3: Forget the Sweep

Delete the second `killer.kill()` (the one after a clean exit). Run `main.py`.

**Hint:** The orphan daemon check fails. A process that exits normally can still leave
children behind; only a kill of the whole group or job finds them.

## Challenge 4: Let the Environment Through

Pass `dict(os.environ)` instead of `scrubbed_env()` to a test run that reads
`MINIRUN_FAKE_SECRET`. What would an API key in your shell look like to a test suite?
