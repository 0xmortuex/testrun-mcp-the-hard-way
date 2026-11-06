"""Module 03: cut a failure down to the lines an agent needs."""

from __future__ import annotations

import re
from dataclasses import dataclass

# pytest --tb=short prints "path/to/file.py:12: in func" followed by the source line.
# The optional drive letter keeps "C:\proj\x.py:3: in f" in one piece.
FRAME = re.compile(r"^(?P<file>(?:[A-Za-z]:)?[^:\n]+?):(?P<line>\d+): in (?P<func>.+)$")
CARETS = re.compile(r"^\s*[\^~]+\s*$")  # the ^^^^^ underline Python 3.11+ adds
LIBRARY = re.compile(r"site-packages|/_pytest/|/pluggy/|/lib/python|/Lib/|<frozen")


@dataclass
class Frame:
    file: str
    line: int
    func: str
    code: str = ""


def parse_traceback(text: str) -> tuple[list[Frame], list[str]]:
    """Return (frames outermost-first, the 'E   ...' lines without the prefix)."""
    frames: list[Frame] = []
    e_lines: list[str] = []
    for raw in text.splitlines():
        if CARETS.match(raw):
            continue
        if raw.startswith("E "):
            e_lines.append(raw[1:].strip())
            continue
        m = FRAME.match(raw)
        if m:
            frames.append(Frame(m["file"].replace("\\", "/"), int(m["line"]), m["func"]))
        elif frames and raw.startswith("    ") and not frames[-1].code:
            frames[-1].code = raw.strip()
    return frames, e_lines


def relevant(frames: list[Frame], keep: int = 5) -> tuple[list[Frame], int]:
    """Drop frames inside libraries, keep the first (the test) and the last few."""
    own = [f for f in frames if not LIBRARY.search(f.file)] or frames[-1:]
    dropped = len(frames) - len(own)
    if len(own) > keep:
        dropped += len(own) - keep
        own = own[:1] + own[-(keep - 1):]
    return own, dropped


def clip_tail(text: str, limit: int = 1500) -> str:
    """Long captured output: keep the END (what happened just before the failure)."""
    text = text.strip("\n")
    if len(text) <= limit:
        return text
    return f"[... {len(text) - limit} chars trimmed ...]\n" + text[-limit:]
