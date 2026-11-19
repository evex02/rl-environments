# RL environments for LLMs

![tests](https://github.com/evex02/rl-environments/actions/workflows/tests.yml/badge.svg)

Open-source environments for reinforcement learning on language models. In each one, an AI model gets a task and is scored by a programmatic check, with a locked-down Docker sandbox for any code it writes. It is a learning project, built to practise environment design: sandboxing untrusted code, writing rewards that are right in both directions, and trying hard to break my own reward functions.

**Status:** two environments, `pyfunc` and `analyst`, are working and tested (255 tests plus one expected failure, run on every push). I have evaluated them with one small local model (`llama3.2:1b`). I have not used them for training. See [Limitations](#limitations).

## What's in the repo

| Folder | What it is |
|---|---|
| `environments/pyfunc/` | Environment 1: write a Python function, graded by running it in a sandbox |
| `environments/analyst/` | Environment 2: multi-turn tool use. Analyse a data table with Python, then give a final number |
| `sandbox/` | The Docker runner for untrusted code, with attack tests. Both environments use it |
| `common/` | Confidence-interval helper used to report results |
| `learning/` | A toy addition environment from my first steps (kept for the history) |
| `analysis/` | Saved baseline results |
| `docs/journal.md` | Lab notebook: every bug, exploit, decision and wrong prediction, in order |

## Environment 1: `pyfunc`

| | |
|---|---|
| **Observation** | A plain-English description of a small function, with three worked examples |
| **Action** | One reply containing a Markdown code block that defines the function |
| **Reward** | 1.0 if the function answers every hidden test input correctly, otherwise 0.0 |
| **Episode** | One prompt, one reply. Each episode uses fresh test inputs generated from a seed |
| **Tasks** | `is_palindrome`, `second_largest`, `run_length_encode`, `fizzbuzz_list`, `merge_intervals` |

How grading works:

1. The reply's code block is extracted.
2. The code is embedded as plain text in a small harness and run inside a Docker container with no network, a read-only filesystem, no special privileges, and limits on memory, processes, time and output.
3. The harness calls the function on generated questions and prints its answers. It never sees the correct answers.
4. Outside the sandbox, the answers are compared with the output of a reference solution. The reward is decided only there. The grader also records why each reward was given (`pass`, `no_code`, `wrong_or_broken`, `timeout`, `flood`) and retries a timed-out run once.

Every episode includes inputs that test each rule in the prompt (for example case, punctuation and digits for palindromes), instead of leaving that to random data.

### Baseline

`llama3.2:1b` through Ollama, temperature 0.7, 600 maximum tokens, 20 episodes per task. Evaluation seeds start at 100000 and are kept apart from any training seeds. Intervals are 95% Wilson intervals.

| Task | This run | 95% interval | First run |
|---|---|---|---|
| is_palindrome | 20/20 | 0.84 to 1.00 | 20/20 |
| second_largest | 8/20 | 0.22 to 0.61 | 11/20 |
| run_length_encode | 20/20 | 0.84 to 1.00 | 19/20 |
| fizzbuzz_list | 14/20 | 0.48 to 0.85 | 17/20 |
| merge_intervals | 18/20 | 0.70 to 0.97 | 18/20 |
| **All** | **80/100** | **0.71 to 0.87** | **85/100** |

Both runs used the same model, settings and questions. 23 of the 100 episodes changed result between them (14 lost, 9 gained; exact sign test p about 0.4), so they cannot be told apart, and differences of a few passes on one task are within noise. The runs share their questions, so I have not pooled them. The first run is kept in `analysis/pyfunc_baseline_before_reasons.json`.

I audited all 20 failures by re-running them. Every one is a genuine model error, such as returning the largest value instead of the second largest, or crashing in its own code. In 9 episodes a first attempt timed out on a loaded machine and was retried; all 9 recovered on the second try, and 4 of them passed. Without the retry, up to 4 of the 80 passes would have scored 0.

## Environment 2: `analyst`

| | |
|---|---|
| **Observation** | A question about a generated CSV table, the file's path and header line, then whatever the model's code printed |
| **Action** | One reply per turn: either one Markdown code block (run as a tool) or one line `FINAL: <number>` (the answer) |
| **Reward** | 1.0 if the final number is within 0.01 of the true value, otherwise 0.0. No feedback on correctness before the end |
| **Episode** | Up to 5 replies. Terminated on a valid `FINAL` line, truncated if the model uses all 5 without one |
| **Tasks** | `mean_clean` (readings coded -999 for missing), `group_median` (outliers, one named group), `pct_change` (percent change between two months' totals) |

The tool is Python (standard library only) in the same sandbox. Every run starts in a fresh container with the data file written to `/tmp/data.csv`, takes at most 5 seconds, and shows the model at most 2000 characters of output. The true answer never enters the sandbox. Each task's generator also makes a list of "wrong approach" answers (averaging in the -999 values, using the mean instead of the median, and so on), and throws away any episode where one of them lands near the truth.

Checked before any model was run:

- A scripted solver that reads the table and calculates each answer scores 1.0 on every task. The same solver off by 0.5, or by 0.02, scores 0.
- The best fixed number a model could answer blindly scores 0.80%, 0.53% and 0.27% on the three tasks (chosen with hindsight over 1500 episodes, so an overestimate).
- Independent re-implementations of the wrong approaches agree with the generators.

### Baseline

Same model and settings as above, 10 episodes per task. Evaluation seeds start at 200000. Prompt v1 is the baseline. Prompt v2 is v1 plus a worked example and one extra sentence, an experiment written after reading the v1 failures on the same episodes, so it is not a held-out test.

| | Prompt v1 | Prompt v2 |
|---|---|---|
| Passes | 1/30 (95% 0.01 to 0.17) | 0/30 (95% 0.00 to 0.11) |
| mean_clean / group_median / pct_change | 1/10, 0/10, 0/10 | 0/10, 0/10, 0/10 |
| Episodes with no valid `FINAL` | 23 | 5 |
| Wrong final answers | 6 | 25 |
| Tool runs in total | 44 | 3 |
| Invalid replies | 63 | 47 |

What this shows: the environment works end to end with a real model (one genuine pass, and the scripted solver passes everything), and `llama3.2:1b` is too weak at this multi-turn format to give a learning signal. Under v1 it often sent several code blocks in one reply. v2 almost removed that habit (38 invalid replies of that kind down to 1), but the model then stopped fencing its code (19 fence lines in the saved v2 transcripts against 363 in v1), so its code was never run, and it guessed final answers. v2 is worse for the purpose of the environment, so I stopped tuning the prompt. I make no claim about stronger models. All the analysis is in [`docs/journal.md`](docs/journal.md).

## Bugs and exploits found in my own designs

Each row was found by writing a test or audit that attacks the design, watching it succeed, fixing the hole, and keeping the test as a guard.

| Environment | Finding | Impact | Fix |
|---|---|---|---|
| sandbox | Output flood | A program printing endlessly made grading take 113 s | Output is capped inside the container; grading dropped to about 10 s |
| pyfunc | Exit early, or force a success exit code | Reward 1.0 with no function written | The answer key stays outside the sandbox; exit codes decide nothing |
| pyfunc | A fixed answer key can be learned | A model that memorised the answers got 1.0 | Fresh inputs every episode; answers come from a reference solution run on the host |
| pyfunc | Weak tests on `is_palindrome` | Plausible wrong solutions earned reward in 39% to 80% of episodes | Every episode includes inputs that test each rule in the prompt |
| pyfunc | Truncated output | A correct FizzBuzz answer scored 0 | The grader sees all output or none |
| sandbox | Spoofed failure reason | Reward unaffected, but the recorded reason could be forged | Status comes from the runner, kept apart from program output |
| analyst | Off-by-one and rounding mistakes | Skipping the first or last data row, or rounding totals before taking a percentage, earned reward in 18%, 23% and 5.6% of episodes | Added to the generators' wrong approaches, so episodes where they pass are rejected |
| both | Machine stalls scored as timeouts | A correct answer scored 0, and (in `analyst`) the model was told its code was too slow | A timed-out run is retried once; errors and floods never are. Cause of the stalls unknown |
| tests | Skipped Docker tests | One run showed 93 passed and 31 skipped while verifying almost nothing | `conftest.py` waits for Docker; `REQUIRE_DOCKER=1` makes a missing Docker stop the run |
| sandbox | *Open:* exit code 124 can fake a timeout | Reward unaffected; the reason is mislabelled and grading repeats once | Recorded as a known limit (an expected-failure test) |

Attacks that did not work, kept as regression tests: patching the answer printer, reading the harness's variables, hedging with two `FINAL` lines, `nan` and `inf` answers, printing `FINAL:` from inside the tool, searching the sandbox for the answer (with a planted control to confirm the search works), flooding the tool's output, and blind guessing.

## Limitations

- **Platforms.** Tested on Windows (Docker Engine inside WSL 2) and on GitHub's Ubuntu runners. macOS has not been tried.
- **One small model.** Only `llama3.2:1b` at temperature 0.7, with 20 episodes per task for `pyfunc` and 10 for `analyst`. The `pyfunc` run-to-run noise is large (see above), and the `analyst` noise was not measured.
- **Difficulty is not tuned.** Two `pyfunc` tasks sit at the ceiling for this model, and `analyst` is too hard for it. Neither gives a trainer much signal for this model.
- **No training run.** I have not shown that either reward is learnable, or that it holds up under optimisation pressure.
- **Machine stalls are unexplained.** About 9% of `pyfunc` episodes in the re-run, and a higher share in the first `analyst` run, had a harmless program time out and then pass on retry. I suspect the laptop's load, but I have not tested it.
- **One unexplained zero.** In the first `pyfunc` baseline, `merge_intervals` episode 19 scored 0 but passed 30 out of 30 when re-graded.
- **Docker is not a perfect security boundary.** It is strong enough for this project. See [`THREAT_MODEL.md`](environments/pyfunc/THREAT_MODEL.md) for what is protected, what is tested and what is open. `analyst` has no standalone threat model yet. Its attack tests are in `environments/analyst/test_analyst_redteam.py`, and the sandbox risks are shared.
- **Audits only cover wrong approaches I wrote.** New ones should be added to the audit lists whenever found.
- **Design documents are first drafts** and do not all match the code. The journal records the differences.

## Running it

You need Python, Docker (Docker Engine inside WSL 2 on Windows, plain Docker on Linux), and Ollama for the baselines.

```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
docker pull python:3.12-slim
.venv\Scripts\python -m pytest -rs
```

On Linux or macOS, use `.venv/bin/python` instead of `.venv\Scripts\python`. The suite expects 255 passes and 1 expected failure, with no skips. Read the skip count, because the Docker tests skip themselves when Docker is not running. To make a missing Docker stop the run instead, set `REQUIRE_DOCKER=1` first (PowerShell: `$env:REQUIRE_DOCKER = "1"`).

To run the baselines (slow, and the time varies a lot with the machine):

```
ollama pull llama3.2:1b
.venv\Scripts\python environments/pyfunc/baseline.py 20
.venv\Scripts\python environments/analyst/analyst_baseline.py 10 llama3.2:1b v1
```

The `pyfunc` run took about 50 minutes for 100 episodes. The `analyst` run took about 2 hours for 30 episodes with prompt v1, and about 20 minutes with v2.

## Documents

- [`docs/journal.md`](docs/journal.md): everything I found and decided, in order, including predictions that turned out wrong
- [`environments/pyfunc/THREAT_MODEL.md`](environments/pyfunc/THREAT_MODEL.md)
- [`environments/pyfunc/DESIGN.md`](environments/pyfunc/DESIGN.md) and [`environments/analyst/DESIGN.md`](environments/analyst/DESIGN.md): first drafts, kept as a record of the original plans
- [`docs/writeup.md`](docs/writeup.md): a short account of what I learned, what I got wrong, and what this does not show

## License

MIT