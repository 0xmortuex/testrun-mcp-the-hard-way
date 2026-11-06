# Module 03: Trimming Tracebacks

## The Concept

The failure text inside the XML is what pytest would have printed. For a failure three calls
deep through a web framework it is a page long, and 80% of it is the framework. An agent
reading it pays for every line and still has to find the one that matters.

What it needs is: **which test, what went wrong, where exactly, and the few frames that lead
there**. [`minirun/trim.py`](../minirun/trim.py) does that.

## Short tracebacks are parseable

With `--tb=short` each frame is two lines:

```
tests\test_cart.py:8: in test_total
    cart.total()
src\cart.py:21: in total
    return self._sum() / len(self.items)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ZeroDivisionError: empty cart
```

One regular expression recognises the header line:

```python
FRAME = re.compile(r"^(?P<file>(?:[A-Za-z]:)?[^:\n]+?):(?P<line>\d+): in (?P<func>.+)$")
```

The optional `(?:[A-Za-z]:)?` is the whole Windows story. Without it, `C:\proj\x.py:7:` is
split at the drive letter's colon and `file` becomes `C`. The line after a header, if indented,
is the source code. Lines starting with `E ` are the exception and assertion detail. The
`^^^^` underline Python 3.11 adds is a line of its own and would otherwise be mistaken for
code, so it is skipped explicitly.

## Which frames matter

```python
LIBRARY = re.compile(r"site-packages|/_pytest/|/pluggy/|/lib/python|/Lib/|<frozen")
```

`relevant()` drops frames inside libraries and the standard library, then caps the rest at
five: the first (the test itself: it says what the test was trying to do) and the last four
(closest to the error). A 30-frame recursion becomes five lines plus a count of what was
omitted, so the agent knows nothing was hidden silently.

If *every* frame is library code (a plugin crashing), it keeps the last one rather than
returning nothing: an empty answer is worse than an unhelpful one.

The function reports the **innermost surviving frame** as `location`: `src/pricing.py:2`, the
line that actually divided by zero, not the line in the test that called it.

## Output: keep the end

Captured stdout is where print-debugging lives, and it can be 30,000 lines. Which part do you
keep? The end: whatever the test printed just before it failed is the context for the failure,
while the beginning is usually setup noise.

```python
def clip_tail(text, limit=1500):
    ...
    return f"[... {len(text) - limit} chars trimmed ...]\n" + text[-limit:]
```

The marker says how much was cut. Silent truncation makes an agent trust a partial view.

## Run It

```bash
python 03-trimming-tracebacks/main.py
```

It parses a Windows-style sample (backslashes, a drive letter, a pluggy frame, the underline),
checks the filtering and capping rules directly, and then runs a real three-level failure with
3,000 lines of noise printed before it.

## What You Learned

- Pick the output format your parser can rely on (`--tb=short`), not the one that looks nicest.
- A location is one frame, chosen on purpose. Show a few more for context, and say how many
  you dropped.
- When you must cut, cut the part with the least information and tell the reader.

Next: [Module 04](../04-rerun-failed/): acting on the result.
