# Break It: JUnit XML Parsing

## Challenge 1: The Default XML Family

Remove `"-o", "junit_family=xunit1"` from the pytest command and run `main.py`.

**Hint:** The default family (xunit2) has no `file=` attribute, so `node_id` falls back to
`classname::name` with dots in the wrong places, and ids no longer match what pytest accepts.

## Challenge 2: Stop at the First Collection Error

Remove `--continue-on-collection-errors`. What does the summary look like for a project with
one broken import and five good test files?

**Hint:** pytest aborts the session. The good tests never run. An agent would see one error
and no information about the rest.

## Challenge 3: Count Collection Errors as Failures

In `Runner.run`, include the collection cases in `failing`. Which assertion in `main.py` catches
it, and why is the distinction worth a separate list?

## Challenge 4: A File With a Space in Its Name

Add `tests/test my file.py` to the project. Does the id round-trip through `rerun_failed`?
Fix whatever breaks.
