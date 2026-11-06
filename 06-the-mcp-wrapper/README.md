# Module 06: The MCP Wrapper

## The Concept

We have a library. An agent cannot import a library; it can call **tools**. The MCP wrapper is
about 60 lines in [`minirun/server.py`](../minirun/server.py), and almost all of the
thinking in it is about three problems.

## 1. Tests take minutes; the protocol loop must not

MCP over stdio is one JSON-RPC conversation on one pipe. If a tool function blocks for three
minutes, the server cannot answer a `ping`, a `tools/list`, or a cancellation for three
minutes. The client may decide the server is dead.

So the blocking function runs in a worker thread:

```python
return await anyio.to_thread.run_sync(functools.partial(fn, *args, **kwargs))
```

`main.py` proves it: it starts a 2-second test through the server, and while it is running asks
for `tools/list`. The assertion is that the list comes back before the test result.

## 2. Errors the agent can act on

In `mcp` 2.x, if a tool raises an arbitrary exception, the client sees only
`Error executing tool run_tests`. The message is hidden on purpose (it could leak internals).
Only a `ToolError` passes its text through. So the tool registration wrapper converts the
exceptions *we raise on purpose* into `ToolError`:

```python
except (UserError, LookupError, ValueError, RuntimeError) as e:
    raise ToolError(e.args[0] if e.args else str(e)) from e
```

Everything else (a real bug) stays hidden. This split matters: "your path is not a directory"
should reach the agent, a stack trace from our own code should not. `main.py` asserts that
three different mistakes arrive with their messages.

(Use `e.args[0]`, not `str(e)`, for `KeyError`-like exceptions: `str(KeyError("x"))` is `"'x'"`
with quotes.)

## 3. The description is the interface

The model reads each tool's docstring to decide when and how to call it. Compare:

```python
"""Run tests."""
```

with

```python
"""Run the project's pytest tests (this EXECUTES the project's code). Returns counts,
and for each failure its id, message, file:line and the relevant traceback frames.
selector: a file, directory or node id such as tests/test_a.py::test_b."""
```

The second tells the agent what comes back, what the argument looks like, and, importantly,
the safety fact. Put that fact in `instructions=` too, where it is read once at
connection time.

## Validate arguments at the boundary

The agent chooses the arguments, so treat them as untrusted:

```python
if selector is not None and selector.startswith("-"):
    raise UserError("selector must be a path or node id, not an option")
```

A selector of `--co` or `-p some_plugin` would otherwise become a pytest *option*, and `-p`
loads and runs arbitrary code. The real server goes further with an allow-list for extra flags
and a check that a selector stays inside the project.

## Return structured data

The tools return dictionaries. The SDK serializes them to JSON text for the model and also
exposes them as structured content. Small, flat, named keys (`outcome`, `summary`, `failures`)
beat a prose paragraph: the agent can quote them and a script can parse them.

## Run It

```bash
python 06-the-mcp-wrapper/main.py
```

It launches `python -m minirun` as a subprocess, speaks MCP to it over real stdio, lists the
tools, runs tests through it, provokes three errors, and checks the concurrency property.
You can add the same server to Claude Code by hand:

```
claude mcp add minirun -- python -m minirun
```

(run from this directory so that `minirun` is importable).

## What You Learned

- Never block the protocol loop; run long work in a thread.
- Decide, on purpose, which errors the agent may see.
- Validate everything the agent controls; put the safety fact in the description.

Next: [Module 07](../07-testing-a-test-runner/): proving it survives the worst projects.
