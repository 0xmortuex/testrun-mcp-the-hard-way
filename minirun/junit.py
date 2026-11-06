"""Module 02: turn pytest's JUnit XML into test cases with exact node ids."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field


@dataclass
class Case:
    id: str
    outcome: str  # passed | failed | error | skipped | xfailed
    seconds: float = 0.0
    message: str = ""
    body: str = ""  # the failure text pytest wrote (traceback, assertion lines)
    stdout: str = ""
    collection: bool = False
    extra: dict[str, str] = field(default_factory=dict)


BANNER = re.compile(r"^-{3,} Captured (Out|Err|Log) -{3,}$")


def captured(text: str) -> str:
    """With junit_logging=all pytest wraps captured output in 'Captured Out' banners."""
    return "\n".join(ln for ln in text.splitlines() if not BANNER.match(ln.strip())).strip()


def node_id(file: str, classname: str, name: str) -> str:
    """Rebuild 'tests/test_a.py::TestX::test_y[p]' from three XML attributes.

    JUnit gives file='tests/test_a.py', classname='tests.test_a.TestX', name='test_y[p]'.
    The module part of classname is the file path with dots, so what follows it
    is the chain of classes. (This is why we ask pytest for junit_family=xunit1:
    only that family writes the file= attribute.)
    """
    file = file.replace("\\", "/")
    module = file[:-3].replace("/", ".") if file.endswith(".py") else file
    if not classname or classname == module:
        return f"{file}::{name}"
    if classname.startswith(module + "."):
        classes = classname[len(module) + 1:].split(".")
        return "::".join([file, *classes, name])
    return f"{file}::{name}"


def parse_junit(path: str) -> list[Case]:
    cases: list[Case] = []
    for tc in ET.parse(path).getroot().iter("testcase"):
        file, name, classname = tc.get("file", ""), tc.get("name", ""), tc.get("classname", "")
        seconds = float(tc.get("time", "0") or 0)
        failure, error, skipped = tc.find("failure"), tc.find("error"), tc.find("skipped")
        out = captured(tc.findtext("system-out", ""))
        if error is not None and error.get("message") == "collection failure":
            # An import error in a test module. Not a failing test: keep it apart.
            cases.append(Case(file.replace("\\", "/"), "error", seconds, "collection failure",
                              error.text or "", collection=True))
            continue
        cid = node_id(file, classname, name)
        el = failure if failure is not None else error
        if el is not None:
            outcome = "failed" if failure is not None else "error"
            cases.append(Case(cid, outcome, seconds, el.get("message", ""), el.text or "", out))
        elif skipped is not None:
            kind = "xfailed" if skipped.get("type") == "pytest.xfail" else "skipped"
            cases.append(Case(cid, kind, seconds, skipped.get("message", "")))
        else:
            cases.append(Case(cid, "passed", seconds))
    return cases
