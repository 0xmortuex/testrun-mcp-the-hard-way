# Break It: The MCP Wrapper

## Challenge 1: Block the Loop

Call `fn(*args, **kwargs)` directly in the wrapper instead of `anyio.to_thread.run_sync`. Run
`main.py`.

**Hint:** The concurrency check fails: `list_tools` cannot be answered until the 2-second test
finishes.

## Challenge 2: Hide the Message

Raise `ValueError` straight out of the tool instead of converting it to `ToolError`. What does
the client print?

**Hint:** With mcp 2.x it is only "Error executing tool ..." and the explanation is lost.

## Challenge 3: Print to Stdout

Add `print("running", path)` at the top of `run_tests`. Run `main.py`.

**Hint:** stdout is the protocol channel. A stray line corrupts the JSON-RPC stream. Use stderr
for logs.

## Challenge 4: Accept Any Selector

Remove the `startswith("-")` check and call `run_tests` with selector `-p`. What does pytest do
with it, and what could `-p some_module` execute?
