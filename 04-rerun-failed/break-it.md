# Break It: Rerun Failed

## Challenge 1: Rerun With an Empty List

Remove the `nothing_to_rerun` early return and call `rerun_failed` after a green run.

**Hint:** `self.run(project, [])` runs the entire suite. The tool whose job is "only the
failures" just ran everything.

## Challenge 2: Delete the Failing File

Remove the `os.path.exists` filter and run `main.py`.

**Hint:** pytest exits with code 4 ("file or directory not found") and writes no report. The
result is a `startup_error` for a mistake that was not an error at all.

## Challenge 3: Two Projects, One Dict

Make `last_failed` a plain list instead of a dict keyed by project, and run two projects
alternately. What does `rerun_failed` run?

## Challenge 4: Many Failures

Make 400 tests fail and rerun them. On Windows the command line is limited to about 32,000
characters. What happens, and how would you fix it (the real server caps the number of ids)?
