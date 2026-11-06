# Break It: Testing a Test Runner

## Challenge 1: Mutation Test the Tree Kill

Comment out the Job Object / `killpg` kill and run only module 07. Does the hang test fail? If
it passes, your test proves nothing. Fix the test, not the kill.

## Challenge 2: Use a Fixed Sleep

Replace `wait_for_file` with `time.sleep(1)` and then read the pid. Run the suite under heavy
CPU load (start a few busy loops). What fails, and is it the code or the test?

## Challenge 3: A Fork Bomb, Gently

Add a project whose test starts 20 child processes that each sleep. After the timeout, are all
20 dead? Extend the proof to check every pid.

## Challenge 4: A Test That Writes Outside the Project

Write a project whose test creates a file in your home directory. Which part of this course
would stop it? (Hint: none. Read the Security section of the testrun-mcp README and say what
would.)
