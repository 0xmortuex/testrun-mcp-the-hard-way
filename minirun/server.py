"""Module 06: the MCP wrapper. Three tools around everything built so far."""

from __future__ import annotations

import functools
import os
from typing import Any

import anyio.to_thread
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from .flaky import flaky_check as _flaky_check
from .runner import Runner

mcp = MCPServer(
    "minirun",
    instructions="Run a project's pytest tests and get a small structured result. "
    "This executes the project's code.",
)
runner = Runner()


class UserError(Exception):
    """Something the agent can fix: bad path, no earlier run, bad argument."""


def tool(fn: Any) -> Any:
    """Register fn as a tool. Two things happen here that the SDK will not do for you:

    * the blocking function runs in a worker thread, so a 3-minute test run does not
      freeze the protocol loop;
    * errors we expect become ToolError. mcp>=2 hides the message of every other
      exception, so without this the agent would only see 'Error executing tool'.
    """

    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await anyio.to_thread.run_sync(functools.partial(fn, *args, **kwargs))
        except (UserError, LookupError, ValueError, RuntimeError) as e:
            raise ToolError(e.args[0] if e.args else str(e)) from e

    mcp.tool()(wrapper)
    return fn


def _project(path: str) -> str:
    if not os.path.isdir(path):
        raise UserError(f"{path!r} is not a directory; pass the project root")
    return os.path.realpath(path)


@tool
def run_tests(path: str, selector: str | None = None, timeout: float = 120) -> dict[str, Any]:
    """Run the project's pytest tests (this EXECUTES the project's code). Returns counts,
    and for each failure its id, message, file:line and the relevant traceback frames.
    selector: a file, directory or node id such as tests/test_a.py::test_b."""
    if selector is not None and selector.startswith("-"):
        raise UserError("selector must be a path or node id, not an option")
    return runner.run(_project(path), [selector] if selector else [], timeout)


@tool
def rerun_failed(path: str) -> dict[str, Any]:
    """Re-run only the tests that failed in the last run_tests for this project."""
    return runner.rerun_failed(_project(path))


@tool
def flaky_check(path: str, test_id: str, n: int = 5) -> dict[str, Any]:
    """Run ONE test n times (2-20) and report the pattern, e.g. PPFPP, and a verdict."""
    return _flaky_check(runner, _project(path), test_id, n)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
