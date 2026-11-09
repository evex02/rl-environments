# pyfunc: design (draft v0.1)

## What this environment is
A single-turn coding environment. The AI is given a description of a small
Python function. It replies with code. A sandbox runs that code against
hidden tests, and the result is the reward.

## What the AI sees (observation)
- A plain-English description of the function.
- The function's name and signature.
- Two worked examples (these are visible, and are not the hidden tests).
- The format rule: put the code in a single Markdown code block marked
  python, and define the function with the exact name given.

## What the AI does (action)
One reply. The episode ends after it.

## How the reward works
- 1.0 if the function passes every hidden test.
- 0.0 otherwise, including: no code block found, a crash, a timeout, a
  wrong answer, or a flood of output.
- Binary on purpose for v1. It is easy to explain and hard to argue
  with. Partial credit (fraction of tests passed) may come later, but it
  makes some cheats easier, so it needs its own decision.

## How grading runs
1. Pull the code block out of the reply.
2. Combine it with the hidden tests.
3. Run the result in the Docker sandbox (no network, read-only, memory and
   time limits).
4. Reward = 1.0 only if the tests report success.

## Starter tasks (5)
1. is_palindrome: ignoring case and punctuation
2. second_largest: of a list, with duplicates and short lists
3. run_length_encode: "aaabcc" becomes "a3b1c2"
4. fizzbuzz_list: the classic, up to n
5. merge_intervals: combine overlapping ranges

## How we will know it works
- A model that does not try (an empty reply) scores 0.
- A reference solution I write for each task scores 1.
- A local model scores somewhere in the middle (aim for roughly 20-80%
  on the full set), reported with a 95% confidence interval.
- The prompt text is saved with the results, because it is part of the
  measurement.

## Expected ways to cheat (to test in red-teaming)
- Hardcode the answers to the visible examples.
- Exit early with a success code before the tests run.
- Print the word the grader looks for.
- Read or overwrite the tests, if they sit in the same place as the code.
- Replace functions the tests rely on.
- Loop forever, use huge memory, or flood the output.

## Out of scope for v1
Multiple turns, tools, internet access, partial credit, more than 5 tasks.