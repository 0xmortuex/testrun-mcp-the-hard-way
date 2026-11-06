"""Module 03: trim a real failure down to the frames that matter."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from common import make_project  # noqa: E402
from minirun.runner import Runner  # noqa: E402
from minirun.trim import Frame, clip_tail, parse_traceback, relevant  # noqa: E402

# What `pytest --tb=short` writes for a failure, including a Windows path, a frame inside
# a library, and the ^^^^ underline that Python 3.11+ adds under the failing expression.
SAMPLE = """\
tests\\test_cart.py:8: in test_total
    cart.total()
src\\cart.py:21: in total
    return self._sum() / len(self.items)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv\\Lib\\site-packages\\pluggy\\_callers.py:103: in _multicall
    res = hook_impl.function(*args)
C:\\Users\\me\\proj\\src\\util.py:7: in _sum
    raise ZeroDivisionError("empty cart")
E   ZeroDivisionError: empty cart
E   (second line of detail)
"""


def main() -> None:
    frames, e_lines = parse_traceback(SAMPLE)
    assert [(f.file, f.line, f.func) for f in frames] == [
        ("tests/test_cart.py", 8, "test_total"),
        ("src/cart.py", 21, "total"),
        (".venv/Lib/site-packages/pluggy/_callers.py", 103, "_multicall"),
        ("C:/Users/me/proj/src/util.py", 7, "_sum"),
    ]
    assert frames[1].code == "return self._sum() / len(self.items)"   # not the ^^^^ line
    assert e_lines == ["ZeroDivisionError: empty cart", "(second line of detail)"]
    print("ok  parsed 4 frames and 2 'E' lines from Windows-style text")

    kept, dropped = relevant(frames)
    assert [f.file for f in kept] == ["tests/test_cart.py", "src/cart.py", "C:/Users/me/proj/src/util.py"]
    assert dropped == 1
    print("ok  the pluggy frame was dropped")

    deep = [Frame(f"src/m{i}.py", i, f"f{i}") for i in range(30)]
    kept, dropped = relevant(deep)
    assert [f.file for f in kept] == ["src/m0.py", "src/m26.py", "src/m27.py", "src/m28.py", "src/m29.py"]
    assert dropped == 25
    print("ok  a 30-frame recursion is cut to the test frame plus the last four")

    text = "".join(f"line {i}\n" for i in range(5000))
    out = clip_tail(text)
    assert out.startswith("[... ") and out.endswith("line 4999") and len(out) < 1600
    print("ok  5000 lines of captured output became", len(out), "chars (the tail)")

    # Now for real: a failure three calls deep, with noisy output before it.
    files = {
        "src/pricing.py": """
            def discount(total, pct):
                return total * (100 - pct) / (pct - pct)


            def final_price(total):
                return discount(total, 10)
        """,
        "tests/test_pricing.py": """
            from src.pricing import final_price


            def test_final_price():
                for i in range(3000):
                    print("debug line", i)
                final_price(100)
        """,
    }
    with tempfile.TemporaryDirectory() as tmp:
        result = Runner().run(str(make_project(Path(tmp) / "proj", files)))
    f = result["failures"][0]
    assert f["id"] == "tests/test_pricing.py::test_final_price"
    assert f["message"] == "ZeroDivisionError: division by zero"
    assert f["location"] == "src/pricing.py:2"                       # where it blew up
    assert [fr["file"] for fr in f["frames"]] == [
        "tests/test_pricing.py", "src/pricing.py", "src/pricing.py"]
    assert f["stdout"].endswith("debug line 2999") and len(f["stdout"]) < 1600
    print("ok  real failure:", f["location"], "-", f["message"])


if __name__ == "__main__":
    main()
