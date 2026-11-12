# RL environments for LLMs

 ![tests](https://github.com/evex02/rl-environments/actions/workflows/tests.yml/badge.svg)  

Open-source environments where an AI model writes code and is scored by running that code in a locked-down sandbox. The project is a work in progress, built to learn environment design for reinforcement learning on language models. It focuses on three things: sandboxing untrusted code, designing rewards that are right in both directions, and trying to break my own reward functions.

**Status:** one environment (`pyfunc`) is working and tested. It has not been used for training yet, and it has only been tested on Windows with WSL 2. See [Limitations](#limitations).

## What's in the repo

| Folder | What it is |
|---|---|
| `environments/pyfunc/` | The environment: write a Python function, get graded in a sandbox |
| `sandbox/` | Docker-based runner for untrusted code, with attack tests |
| `common/` | Confidence-interval helper used to report results |
| `learning/` | A toy addition environment from my first steps (kept for the history) |
| `analysis/` | Saved baseline results |
| `docs/journal.md` | Lab notebook: every bug, exploit and decision, in order |

## The `pyfunc` environment

| | |
|---|---|
| **Observation** | A plain-English description of a small function, with three worked examples |
| **Action** | One reply containing a Markdown code block that defines the function |
| **Reward** | 1.0 if the function answers every hidden test input correctly, otherwise 0.0 |
| **Episode** | One prompt, one reply. Each episode uses fresh test inputs generated from a seed |
| **Tasks** | `is_palindrome`, `second_largest`, `run_length_encode`, `fizzbuzz_list`, `merge_intervals` |

How grading works:

1. The reply's code block is extracted.
2. The code is embedded as plain text in a small harness, and run inside a Docker container with no network, a read-only filesystem, no special privileges, and limits on memory, processes, time and output.
3. The harness calls the function on generated questions and prints its answers. It never sees the correct answers.
4. Outside the sandbox, the answers are compared with the output of a reference solution. The reward is decided only there.

## Baseline

`llama3.2:1b` (via Ollama, temperature 0.7, 600 max tokens), 20 episodes per task, evaluation seeds kept separate from any training seeds. Intervals are 95% Wilson intervals.

| Task | Passed | 95% interval |
|---|---|---|
| is_palindrome | 20/20 | 0.84 to 1.00 |
| second_largest | 11/20 | 0.34 to 0.74 |
| run_length_encode | 19/20 | 0.76 to 0.99 |
| fizzbuzz_list | 17/20 | 0.64 to 0.95 |
| merge_intervals | 18/20 | 0.70 to 0.97 |
| **All** | **85/100** | **0.77 to 0.91** |

Every reply contained a code block, so each failure is a task failure and not a formatting one. I audited all 15 zeros: 14 are clear model errors. One (`merge_intervals`, episode 19) scored 0.0 during the run but passed 30 out of 30 when re-graded, and its cause is unknown. The results file is `analysis/pyfunc_baseline.json`.

## Bugs and exploits found in my own design

Each row was found by writing a test that attacks the design, watching it succeed, fixing the hole, and keeping the test as a guard. Details are in [`docs/journal.md`](docs/journal.md).

| Finding | Impact | Fix |
|---|---|---|
| Output flood | A program printing endlessly made grading take 113 s | Output is capped inside the container; grading dropped to about 10 s |
| Exit early, or force a success exit code | Reward 1.0 with no function written | The answer key stays outside the sandbox; exit codes decide nothing |
| Fixed answer key can be learned | A model that memorised the answers got 1.0 | Fresh inputs for every episode, answers from a reference solution run on the host |
| Weak tests on `is_palindrome` | Plausible wrong solutions earned reward in 39% to 80% of episodes | Every episode now includes inputs that test each rule in the prompt |
| Truncated output | A correct FizzBuzz answer scored 0 | The grader sees all output or none |
| Spoofed failure reason | Reward unaffected, but the recorded reason could be forged | Status comes from the runner, kept apart from program output |
| *Open:* exit code 124 can fake a timeout | Reward unaffected; the reason is mislabelled and grading repeats once | Recorded as a known limit (an expected-failure test) |

## Limitations

- **Tested on Windows (Docker in WSL 2) and on GitHub's Ubuntu runners.** The sandbox picks its Docker command by platform. macOS has not been tried.
- **One small model, one prompt, 20 episodes per task.** The baseline says little about other models or settings.
- **Difficulty is not tuned.** Two tasks are close to the ceiling for this model, so they would give a trainer little signal.
- **No training run yet.** I have not shown the reward is learnable or hard to exploit under training pressure.
- **Docker is not a perfect security boundary.** It is strong enough for this project, and stronger isolation exists. A standalone threat model document is still to be written.
- **The baseline predates a grader change.** Timeouts are now retried once and the reason for each score is recorded. The saved results do not include those reasons.
- `environments/pyfunc/DESIGN.md` is the first draft and no longer matches the implementation.

## Running it

You need Python, Docker Engine inside WSL 2 (Ubuntu), and Ollama for the baseline.

```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
docker pull python:3.12-slim
.venv\Scripts\python -m pytest -rs
```

The first run pulls the `python:3.12-slim` image. The suite expects about 121 passing tests and 1 expected failure, with no skips. Read the skip count: the Docker tests skip themselves when Docker is not running.

To run the baseline (slow, about 50 minutes for 20 episodes per task on a CPU):

```
ollama pull llama3.2:1b
.venv\Scripts\python environments/pyfunc/baseline.py 20
```

## License

MIT