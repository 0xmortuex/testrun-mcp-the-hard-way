# Module 02: JUnit XML Parsing

## The Concept

Module 01 gives us the bytes a test run printed. Parsing those bytes is the trap: pytest's
console output changes with `-q`, `-v`, plugins, terminal width, locale and version. There is
a stable, machine-readable alternative that every serious runner can write:

```
pytest --junitxml=report.xml
```

JUnit XML was designed for CI servers. It lists every test case with its outcome, duration,
failure text and captured output. We parse that and ignore the console.

## Asking pytest for the right XML

[`minirun/runner.py`](../minirun/runner.py) builds this command:

```python
[sys.executable, "-m", "pytest", f"--junitxml={xml}",
 "-o", "junit_family=xunit1",   # adds the file= attribute (see below)
 "-o", "junit_logging=all",     # include captured stdout/stderr of failures
 "-p", "no:cacheprovider",      # do not write .pytest_cache into the user's project
 "--tb=short", "-v", "--continue-on-collection-errors"]
```

Three choices matter:

- **`junit_family=xunit1`** because only that family writes the `file=` attribute on each
  `<testcase>`. We need it to rebuild the real test id (next section).
- **`--continue-on-collection-errors`**: by default, one test file that fails to import
  *aborts the whole run*. The agent would learn nothing about the other 400 tests. With the
  flag, the good files run and the bad one is reported on the side.
- **`-p no:cacheprovider`**: a tool that silently drops files into your project is a bad
  guest. The XML goes to a temporary directory that is deleted afterwards.

## What a `<testcase>` gives you

```xml
<testcase classname="tests.test_a.TestK" name="test_p[a b]" file="tests\test_a.py" line="8" time="0.002">
  <failure message="assert 1.0 == 3">tests\test_a.py:6: in test_fail
    assert f(1) == 3
E   assert 1.0 == 3</failure>
</testcase>
```

No node id, just three attributes. [`junit.node_id`](../minirun/junit.py) rebuilds
`tests/test_a.py::TestK::test_p[a b]`:

1. normalize `file` to forward slashes (Windows writes backslashes);
2. turn the file path into a dotted module name, `tests.test_a`;
3. whatever follows that prefix in `classname` is the chain of classes.

Why not just use `classname` and `name`? Because `classname` is dotted, and a directory called
`my.pkg` is indistinguishable from a package and a module. Starting from the file path avoids
guessing.

## Outcomes are encoded in children

| XML | Meaning |
|---|---|
| no child | passed |
| `<failure>` | an assertion (or any exception) in the test body |
| `<error>` | a problem outside the body: a fixture, setup or teardown |
| `<skipped type="pytest.skip">` | skipped, `message` is the reason |
| `<skipped type="pytest.xfail">` | expected failure that failed |
| `<error message="collection failure">` | **not a test**: a module could not be imported |

The last row is the important one. A collection failure has a `<testcase>` too, named after
the module, but it is a different kind of problem. Mixing it into "failures" sends an agent to
read assertions when it should fix an import. `parse_junit` flags it (`collection=True`) and
`Runner.run` reports it in a separate `collection_errors` list and a separate count.

Non-ASCII parameter ids are escaped by pytest itself (`test_param[你好]`, literal
backslash-u). We keep them exactly as pytest wrote them, because that is also what pytest
accepts back when we re-run the test (Module 04).

## When there is no XML

pytest writes the report when the session *finishes*. If it never gets there, there is no
file, and that is information:

- exit code 2, 3 or 4 and no file: it could not start (broken `conftest.py`, usage error);
- any other exit code and no file: the process died (`os._exit`, a segfault);
- the timeout fired: it hung.

`Runner.run` reports these as `startup_error`, `crashed` and `timeout`, each with the tail of
the console output, and, using the `-v` trick in Module 07, the name of the test that was
running.

## Run It

```bash
python 02-junit-xml-parsing/main.py
```

The demo builds a project in a temporary directory with a passing test, two failures, a
parametrized unicode id, a skip and a module that imports something that does not exist, runs
real pytest and asserts the counts and ids exactly.

## What You Learned

- Prefer a machine-readable report to scraping console text.
- Reconstruct identity from stable attributes, not from presentation.
- Separate "a test failed" from "the tests could not be loaded".
- "No report" is a result with its own meaning.

Next: [Module 03](../03-trimming-tracebacks/): what to do with the failure text.
