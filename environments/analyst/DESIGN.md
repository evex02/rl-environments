# analyst: design (draft v0.1)

## What this environment is
A multi-turn tool-use environment. The model is given a small data table
(generated fresh for each episode) and a question about it. It can run Python
code in the sandbox to look at the data, and it ends the episode by giving a
final number. The reward comes from comparing that number with a value
computed on the host.

## What the model sees (observation)
- First message: the question, a description of the columns, where the data
  file is (/tmp/data.csv), what the tool does, and the rules for replying.
- Later messages: whatever its last code printed (first 2000 characters).

## What the model does (action)
Each turn, the model sends exactly one of:
- A reply with exactly one Markdown code block marked python. That is a tool
  call. The code runs in the sandbox.
- A reply with exactly one line of the form `FINAL: <number>`. That is the
  final answer, and the episode ends. Any code in that reply is not run.

Anything else is invalid: no code runs, the model is told what was wrong, and
the turn is used up. Invalid replies include: more than one code block, more
than one FINAL line, neither of the two forms, and a FINAL line whose value is
not a plain number (no words, ranges, nan or inf).

## The tool
Python in the same Docker sandbox as the pyfunc environment, using the
standard library only. Every run is a fresh container, so nothing carries over
between turns. The data is written to /tmp/data.csv before the model's code
runs. Each run has a 5 second limit, and the output shown to the model is cut
to 2000 characters.

## Episodes
At most 5 replies per episode.
- terminated: the model gave a valid final answer.
- truncated: the model used all 5 replies without one. Reward 0.

## Reward
1.0 if the final number is within the task's tolerance of the true value,
otherwise 0.0. The model gets no feedback on correctness before the end.

## How the data and the truth are made
Per episode, from a seed: a table is generated, and a trusted reference
function on the host computes the true answer. The table is sent to the
sandbox (the model is meant to see it). The true answer never is.

## Starter tasks (3)
1. mean_clean: some readings are missing and coded as -999. Question: the mean
   of the valid readings. Trap: averaging all rows.
2. group_median: values for several groups, with outliers. Question: the
   median for one named group. Traps: using the mean, or the wrong group.
3. pct_change: several rows per month. Question: the percent change in the
   monthly total between two named months. Traps: averaging instead of
   summing, using only the first row of each month, or dividing the wrong way.

All answers are to 2 decimal places, with a tolerance of 0.01.

## How we will know it works
- Oracle test: a scripted "model" that runs the reference code through the real
  tool and then reports the printed number must score 1.0 on every task.
- Wrong-approach audit: a list of plausible wrong calculations (run on the
  host). None may land within tolerance in any of 200 episodes.
- Cheat tests (below) must all score 0.
- Baseline with a local model: pass rate with intervals, the reason for each
  score (pass, wrong_answer, no_final, bad_format), average turns used, and
  how often the tool crashed.

## Expected ways to cheat
- Print `FINAL: x` from the tool code, hoping the tool output is read as an answer.
- Guess a number on turn 1.
- Send several FINAL lines to hedge.
- Write nan, inf, a range, or a word after FINAL.
- Search the sandbox (files, environment variables) for the true answer.
- Waste turns or time, or flood the output.
- Use a calculation that is wrong but close enough to be accepted.

## Out of scope for v1
State kept between tool calls, pandas or numpy, more than 3 tasks, partial
credit, grading the reasoning, multiple tables.