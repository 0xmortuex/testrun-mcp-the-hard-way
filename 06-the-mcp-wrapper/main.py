"""Module 06: launch the minirun MCP server over real stdio and use it like an agent would."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import anyio
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from common import make_project  # noqa: E402

PROJECT = {
    "tests/test_a.py": """
        def test_ok():
            assert True


        def test_bad():
            assert 1 == 2, "one is not two"
    """,
    "tests/test_slow.py": """
        import time


        def test_slow():
            time.sleep(2)
    """,
}


async def demo() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        project = str(make_project(Path(tmp) / "proj", PROJECT))
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "minirun"], cwd=str(ROOT))
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            init = await session.initialize()
            assert init.server_info.name == "minirun"
            tools = {t.name: t for t in (await session.list_tools()).tools}
            assert set(tools) == {"run_tests", "rerun_failed", "flaky_check"}
            assert "EXECUTES the project's code" in (tools["run_tests"].description or "")
            print("ok  tools:", sorted(tools))

            res = await session.call_tool(
                "run_tests", {"path": project, "selector": "tests/test_a.py"})
            assert not res.is_error
            out = json.loads(res.content[0].text)
            assert out["summary"]["passed"] == 1 and out["summary"]["failed"] == 1
            assert out["failures"][0]["id"] == "tests/test_a.py::test_bad"
            print("ok  run_tests over MCP:", out["failures"][0]["message"])

            res = await session.call_tool("rerun_failed", {"path": project})
            assert json.loads(res.content[0].text)["summary"]["total"] == 1

            # Errors the agent can act on must survive the trip.
            res = await session.call_tool("run_tests", {"path": str(Path(tmp) / "nope")})
            assert res.is_error and "is not a directory" in res.content[0].text
            res = await session.call_tool("run_tests", {"path": project, "selector": "--co"})
            assert res.is_error and "not an option" in res.content[0].text
            res = await session.call_tool("rerun_failed", {"path": tmp})
            assert res.is_error and "call run_tests first" in res.content[0].text
            print("ok  errors reach the agent with their message")

            # The server stays responsive while a test run is in progress (worker thread).
            seen: dict[str, object] = {}

            async def slow() -> None:
                seen["slow"] = await session.call_tool(
                    "run_tests", {"path": project, "selector": "tests/test_slow.py"})

            async with anyio.create_task_group() as tg:
                tg.start_soon(slow)
                await anyio.sleep(0.8)
                await session.list_tools()
                assert "slow" not in seen, "list_tools had to wait for the test run"
            print("ok  list_tools answered while a test was still running")


if __name__ == "__main__":
    anyio.run(demo)
