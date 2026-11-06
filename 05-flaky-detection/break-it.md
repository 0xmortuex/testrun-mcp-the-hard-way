# Break It: Flaky Detection

## Challenge 1: Run N Times in One Process

Replace the loop with `pytest --count`-style repetition inside a single process (for example
by passing the same id N times). Does the counter-file test still show `PFPFP`?

**Hint:** Think about what pytest does with duplicate ids, and about module-level state shared
by every iteration in one process.

## Challenge 2: Treat "No Tests" as a Pass

Delete the `startup_error / crashed / no_tests` check. Call `flaky_check` with a misspelled id.

**Hint:** Zero collected tests means zero failures: you get `PPPPP` and `stable_pass` for a test
that does not exist.

## Challenge 3: A Test That Hangs Once

Write a test that sleeps forever on its second run (use the counter file). What does the pattern
look like, and what does your timeout cost you in total?

## Challenge 4: Order-Dependent Flakiness

Write two tests where the second fails only if the first ran before it in the same process.
Run `flaky_check` on the second. Why does it say `stable_pass`, and what should the tool tell the
agent?
