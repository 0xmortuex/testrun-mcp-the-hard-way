# Break It: Trimming Tracebacks

## Challenge 1: Drop the Drive Letter Group

Change `FRAME` so the file group is `[^:\n]+?` with no `(?:[A-Za-z]:)?`. Feed it the Windows
sample in `main.py`.

**Hint:** `C:/Users/me/proj/src/util.py:7` is split at the first colon: file `C`, and the
line number never matches.

## Challenge 2: Keep Every Frame

Return `frames` unfiltered from `relevant()`. Run the three-level failure. How many frames does
the agent get for a failure inside Django or FastAPI?

## Challenge 3: Keep the Head of the Output, Not the Tail

Change `clip_tail` to `text[:limit]`. Print 5,000 lines then fail. Which line does the agent
see, and does it help?

## Challenge 4: A Recursion Error

Write a test that recurses infinitely. pytest's traceback has hundreds of identical frames.
Does `relevant()` still return something readable?
