## Project Journal
- Week 1: Installed tools and cloned the repo

## Exploit found: retry guessing
- What: the AI could answer repeatedly in one episode until correct.
- How I found it: I did it by accident while playing the environment.
- Fix: the episode ends after one reply (test: test_cannot_answer_twice_in_one_episode).

## Finding: format instructions
- Without a format reminder, llama3.2:1b followed the 'Answer:' format in 2/20 replies (reward 0.10).
- With a reminder, 20/20 (reward 1.00). Maths was right in all cases both times.
- Takeaway: the prompt is part of the environment and must be documented.

## Difficulty Results
Difficulty	Reward	What it means for training
2-digit	    1.00    Too easy, nothing to learn from
3-digit	    0.75	Useful
4-digit	    0.55	Useful, close to the ideal
5-digit	    0.10	Almost too hard, since most replies are wrong

## Known weaknesses of run_code.py (not yet a sandbox)
- Untrusted code can read, change or delete my files.
- It can use the network.
- Output is only cut to 2000 characters after it has all been collected, so a program that prints endlessly could use up memory.
- Fix plan: run it inside a Docker container with no network, a read-only filesystem and memory limits.

## Sandbox v1: Docker (run_code_docker.py)
- Fixed: file access, network access, writing outside /tmp, running as root, memory use, runaway loops.
- Tests: scratch/test_run_code_docker.py (8 attack tests).
- Lesson: killing the host-side command does not stop the container. The time limit has to run inside the container, with a cleanup step as backup.
- Still untested: a program that prints huge amounts of output, a fork bomb, and a program that fills /tmp.
- Rule: AI-written code only goes through run_python_sandboxed, never run_python.

## Red-team round 1 (sandbox)
- Fork bomb: contained by --pids-limit 64. Sandbox still works afterwards. (test_fork_bomb_is_contained)
- Disk filler: contained by the 16 MB /tmp limit. (test_filling_tmp_is_contained)
- Output flood: REAL HOLE. The runner collected all output before truncating, so a program could make the host read hundreds of MB. Fixed by streaming the output and stopping at 100 KB. (test_output_flood_is_cut_off)
- Lesson: a limit that is applied after collecting everything is not a limit.

- Output flood, second finding: even with a streaming cap, the flood took 113 s to resolve, and the container was still running a minute after its 5 s limit. Stopping from outside is too late.
- Fix: the program writes its output to a file in the container's 16 MB /tmp; only the first 100 KB is sent out. A flood is contained inside the container.
- Lesson: contain a problem where it happens, not where you notice it.

## pyfunc red-team round 1: fix
- Fix: the answer key stays on the host. The sandbox only gets the questions and prints the function's answers. The host compares them. Exit codes no longer decide anything.
- AI code is embedded as an escaped string (repr), so it can't alter the harness text.
- Results compared as JSON text, so True != 1.
- Duplicate answer lines for the same question are rejected.
- Regression tests: 5 cheats in test_pyfunc.py, all must score 0.0.
- Principle: don't let the thing being judged run in the same place as the judge or the answer key.

## Known remaining weaknesses (to attack in round 2)
- Forged answer lines: the AI can print fake RESULT lines then exit. With boolean answers, a blind guess of all 8 answers has a 1 in 256 chance of matching. Not zero, and RL trains on thousands of attempts.
- The AI could find and copy an unpredictable token if I add one, by inspecting the running program.
- Output is capped at 2000 characters, so long legitimate answers would be cut off and score 0.
- Only single-argument functions are supported.

## pyfunc red-team round 2: learnable answer key
- Attack: a model that has learned the fixed answers (from repeated reward feedback) prints them and exits. Scored 1.0 with no function. (CHEATS["memorised_key"])
- Why it matters: RL shows the model its reward thousands of times, so any fixed key leaks.
- Fix: questions are generated fresh per episode from a seed. Expected answers come from the reference solution, run on the host (trusted code only). 20 inputs, mix of True and False, so a constant guess fails.
- Residual: a forger who knows one episode's answers still wins that episode. This only matters if episodes repeat.

## Remaining weaknesses
- Seeds must never repeat during training; keep separate seeds for evaluation.
- Only one task so far. More tasks, and tasks not solvable by a one-line trick, are needed.
- Output is capped at 2000 characters, so long legitimate answers would be cut off.
- The AI's code can inspect the harness (it can see the inputs). It can't see the answers, but this needs a proper test.
- Only single-argument functions are supported.

## Lesson: a passing cheat test may pass by accident
- memorised_key first passed against the fixed-key grader, which I expected to fail.
- Likely cause: os._exit(0) skips flushing Python's output buffer, so the fake answers were lost.
- Fix to the test: flush=True. A cheat test is only valid if it succeeds against a deliberately weak grader.

## pyfunc environment class
- PyFuncEnv: reset() picks a task and a fresh episode seed; step() grades once, then the episode is done.
- Same environment seed reproduces the same sequence of episodes.
- Reused lessons: one reply per episode (done flag), fresh test inputs per episode.
- Next: more tasks, then baselines with a local model.

## pyfunc: false negative (honest answers scored 0)
- Bug: the sandbox truncated all output to 2000 chars. FizzBuzz answers across 20 inputs exceed that, so a CORRECT solution lost the later answers and scored 0.0.
- Found by: the reference-solution test for the new fizzbuzz_list task (predicted from reading the code, then confirmed).
- Fix: run_python_sandboxed takes keep_chars; the grader asks for the full flood limit (100 KB). Anything over that is still rejected as a flood, so the grader sees all output or none.
- Guards: test_reference_solution_passes_on_other_seeds (every task, several episodes), test_legitimate_output_fits_under_the_cap (2x safety margin), test_output_is_truncated_unless_a_larger_limit_is_requested.
- Lesson: false negatives hurt as much as exploits. The reward must be right in both directions, and a task isn't finished until its reference solution passes on many episodes.

## pyfunc baseline v1 (llama3.2:1b, temp 0.7, 10 episodes per task)
- Overall 40/50 = 0.80 (95% 0.67 to 0.89). Code block rate 1.00.
- Per task: palindrome 10/10, second_largest 4/10, run_length_encode 9/10, fizzbuzz 7/10, merge_intervals 10/10.
- Audit of the 10 failures (audit_failures.py): all honest model errors; no grader bugs, no ambiguous prompts.
- Limits: the audit only checks zeros. Passes that shouldn't be passes are not covered yet.
- Two tasks sit at the ceiling for this model (palindrome, merge_intervals), so they give a trainer little signal.
- Suspicion: palindrome inputs may not test the case rule (mirrored strings are exact palindromes).

## pyfunc red-team round 3: weak tests let wrong solutions earn reward
- Audit (audit_wrong_solutions.py): plausible wrong palindrome solutions earned reward 1.0 in 39-80% of episodes (raw reversal 78/200, keeps punctuation 81/200, drops digits 80/200, case-sensitive 161/200). merge_intervals "keeps the last end" got 1/200.
- Cause: the generator built palindromes by exact mirroring, so case/punctuation/digit rules were rarely tested. Random strings almost never exercised them.
- Why it matters: a trainer would learn that ignoring parts of the prompt still earns reward.
- Fix: every episode now includes guaranteed "trap" inputs for each rule (case, punctuation, digits), plus a nested-interval case for merge_intervals.
- Guards: test_known_wrong_solution_never_earns_reward (17 wrong solutions x 200 episodes, must all score 0), test_reference_passes_every_audit_episode.
- Principle: don't rely on random inputs to hit a rule. Guarantee coverage, then measure it.
- Limit: the guard only covers wrong solutions I thought of. Add new ones to WRONG in audit_wrong_solutions.py whenever I (or a model) find one.
- The baseline v1 palindrome result (10/10) was measured with the weak tests. Re-run the baseline after tasks are final.

## pyfunc baseline v2 (llama3.2:1b, temp 0.7, 20 per task, after trap inputs)
- Overall 85/100 = 0.85 (95% 0.77 to 0.91). Palindrome 20/20, second_largest 11/20, run_length_encode 19/20, fizzbuzz 17/20, merge_intervals 18/20.
- Audit: 14 of 15 failures are honest model errors. One (merge_intervals episode 19) scored 0.0 but re-graded 30/30 PASS (regrade.py).
- Cause undetermined. The first re-grade took 9.6 s against ~1 s typical, so slow outliers exist on this machine. Hypothesis, untested: the in-container 5 s limit includes the wait for the code to arrive over the pipe, so a pipe stall can look like a timeout.
- Design flaw found: the baseline recorded only the reward, so an infrastructure hiccup was indistinguishable from a wrong answer.
- Fix: grade_detailed returns (reward, reason, attempts). Timeouts are retried once; wrong answers and floods never are, so a retry opens no new cheat. The env exposes env.info. Baselines now record the reason for each score.
- Cost: genuine infinite loops now take ~2x as long to grade.
- Known limits: the runner reports status as magic strings ("timed out") in the same channel as program output, so a program can print that text to mislabel its own reason (reward unaffected). Docker-level failures are not yet separated from wrong answers. Fixing the second needs the runner to return its exit code.
- If the 0.0 was a false negative, merge_intervals is 19/20 and overall is 86/100.

## pyfunc red-team round 4: the harness
- Attack 1 (replace json.dumps so every printed answer is 'true'): the attack runs, but earns nothing. The answer key never enters the sandbox.
- Attack 2 (read the harness's variables with sys._getframe): the AI can see the question list. No answers are in it. Rule: everything inside the sandbox is public to the AI, so never put answers or secrets in a program that goes in.
- Attack 3 (print the runner's status text, then exit): reward stayed 0.0, but the REASON was spoofed ('timeout' or 'flood'), and a fake timeout also triggered a retry. Impact: corrupts the reasons recorded in baselines, doubles grading time for that reply. No reward impact.
- Cause: status and output travelled in the same channel (magic strings in the output).
- Fix: run_python_detailed returns (status, output) with the status decided by the runner from the exit code, a byte count and a timer. The grader no longer reads status from the output.
- Guards: test_program_output_cannot_spoof_the_failure_reason (2 cases), test_output_that_says_timed_out_is_just_output, runner status tests.

## Known remaining weaknesses
- Exit code 124 means "timeout", and a program can exit with that code itself. Documented as an xfail test (test_exit_code_124_cannot_spoof_a_timeout). Effect: the reason says 'timeout' and the grading is repeated once. Reward unaffected. Possible fix: also require that the wall-clock time reached the timeout.
- A program that ignores the stop signal is only removed by the 20 s backstop. Untested.
- Docker-level failures (e.g. the container fails to start) are not separated from 'wrong_or_broken'.
- Two tasks sit near the ceiling for llama3.2:1b.

- Guard (REQUIRE_DOCKER=1) not verified by a real shutdown: Docker restarts itself on demand here, so I could not stage the failure. Mitigation: read the skip count at the end of every run (-rs).

## Repo tidy
- Moved scratch/ into sandbox/, common/, learning/, and journal.md into docs/. Only moves and path-line edits; no logic changed.
- Deleted the unsafe subprocess runner (run_code.py) and its tests, plus two one-off debug scripts. They remain in Git history.
- Test count went from 124 passed + 1 xfailed to 121 passed + 1 xfailed, because 3 tests belonged to the deleted runner.
- All scripts verified to import after the move (runpy check).

## Moved out of OneDrive
- Cloned a fresh copy and rebuilt .venv, instead of moving the folder (a venv hard-codes its location, and OneDrive can interfere with Git and thousands of small files).
- Verified: pytest gives 121 passed, 1 xfailed, 0 skipped in the new location.
- The sandbox does not depend on the project's location: code is piped into the container, and no host folders are mounted.

## Sandbox made portable (prepares for CI)
- Problem: every Docker call hardcoded the 'wsl -u root' prefix, so nothing would run on GitHub's Linux test machines.
- Fix: docker_command() picks the prefix by platform (wsl on Windows, plain docker elsewhere). One shared docker_works() replaces five copies of the check.
- Tests (no Docker needed): the chosen command for win32, linux and darwin, and that the run command contains no wsl on Linux.
- Caveat: I have only run this on Windows. The Linux path is untested until CI runs it. Expect the first CI run to possibly find Linux-only differences.
- Risk noted: the 20 s backstop timer starts before docker run finishes. If the python:3.12-slim image has to be downloaded first, a slow download could be reported as a timeout. CI will pre-pull the image.

## CI on GitHub Actions
- Workflow runs the full suite on every push and pull request, on ubuntu-latest with Python 3.12, with REQUIRE_DOCKER=1 so missing Docker fails the run instead of skipping.
- The sandbox image is pulled in its own step first, so a slow download cannot be mistaken for a timeout.
- Local environment is Python 3.15 on Windows, so CI also checks a second Python version and a second operating system.
- Findings from the first runs: (fill in)

## Threat model written
- environments/pyfunc/THREAT_MODEL.md: assets, adversary, trust boundary, 15 threats mapped to guard tests, residual risks, contributor rules.
- Honest gaps recorded: dropped capabilities are not directly tested; exit-code-124 spoof is open; wrong-solution coverage is limited to the ones I wrote.

## Second environment: analyst (design)
- Multi-turn tool use: generated table, Python tool in the same sandbox (stdlib only), up to 5 replies, final answer as `FINAL: <number>`, binary reward from a host-side reference.
- Decisions: fresh container per code run; no correctness feedback before the end; invalid replies cost a turn; 3 starter tasks.
- Design written before any code. Same method as pyfunc: oracle test, wrong-approach audit, cheat tests, then baseline.

## analyst: reply parsing and task generators
- Reply parsing (analyst_parsing.py): a reply is a tool call (one code block), a final answer (one FINAL line), or invalid (no_action, multiple_code_blocks, multiple_final, bad_number). FINAL wins over code in the same reply; FINAL text inside a code block does not count; the format is deliberately strict (uppercase FINAL:, plain decimal numbers only). The baseline will show whether this is too harsh.
- Module names are prefixed analyst_ because pyfunc already has tasks.py, and two same-named modules on the path shadow each other.
- Task generators (analyst_tasks.py): three tasks. Each episode carries decoys, the answers that wrong approaches would give. Episodes where a decoy lands within 0.05 of the truth are thrown away, so a wrong method cannot pass by coincidence. Same lesson as the palindrome task.
- Independent check: tests recompute each answer from the CSV text with different code from the generator.
- Tolerance is 0.01 on answers given to 2 decimal places.

## analyst: the environment class
- AnalystEnv.reset()/step() with the five-part return (observation, reward, terminated, truncated, info). The tool is injectable (run_tool), so 33 tests run with a pretend tool and no Docker.
- Changes from the design: a code reply on the last turn is not run (the episode ends anyway); episode reasons are pass / wrong_answer / no_final, with invalid replies counted separately instead of a fourth reason; the prompt gives the CSV header, not a column description.
- The tool's status (ok/error/timeout/flood) comes from the runner, never from program output. A FINAL line printed by tool code is not an answer (test_final_text_printed_by_the_tool_is_not_an_answer).
- The true answer never enters the sandbox program or any message (test with a sentinel value).
- Tolerance: 0.01, compared with a 1e-9 allowance for floating-point rounding.
- Next: the oracle test (a scripted model that runs the reference calculation through the real sandbox must score 1.0 on every task), then the wrong-approach audit and cheat tests.

## analyst: oracle test (real sandbox)
- A scripted solver (not an AI) reads the question, writes Python that calculates the answer from /tmp/data.csv, runs it through the real sandbox, and replies FINAL. It must score 1.0 on every task across 6 seeds. The oracle's code is written separately from the generators.
- Negative control: the same oracle reporting an answer that is off by 0.5, or by 0.02, must score 0. This shows the 1.0 is not a vacuous pass from a loose tolerance.
- Through the real loop: each tool run starts in a fresh container with the data file restored (tampering does not persist), crashes are reported, infinite loops are reported.
- Limit: no retry on timeouts in this environment (the pyfunc grader has one).

## analyst red-team round 1: cheats
- Best fixed guess (chosen with hindsight over 1500 seeds, so an overestimate): mean_clean 0.80%, group_median 0.53%, pct_change 0.27%. Test threshold: under 2%. A control task with a constant answer scores 100%, so the measure can detect a leak.
- Hedging with two FINAL lines: invalid, costs a turn, the episode continues and a clean answer still scores.
- nan, inf, ranges, 1e3 and percentages: invalid, no score, episode continues.
- FINAL text printed by the tool: never read as an answer. Control: the same text sent as a reply is accepted.
- Searching the sandbox (environment variables, /proc command lines, /tmp, the harness's own variables) for the true answer finds nothing. A planted control confirms the scan can find a match.
- Flooding the tool: reported to the model as too much output; the episode continues and a final answer still scores.
- No reward holes found in this round. The tests remain as regression guards.

## analyst: first real model on the environment (smoke test, 3 episodes, llama3.2:1b)
- Result: 0/3 (95% 0.00 to 0.56). Meaningless as a rate, so I read the transcripts instead (show_transcripts.py).
- Model behaviour, all fair: code without fences; two code blocks per reply, repeated three times despite being told; reading the header row as data; FINAL guesses written alongside code before seeing any output. Final answers (0.00, 42.50, 0.23, 0.00) matched none of the wrong approaches. A lenient parser would still have scored all three 0.
- Environment finding: a trivial program (sum of a ~20-row CSV) reported "ran out of time" on turn 1, then nearly identical code ran fine on turn 2. The second spurious timeout seen (the first: pyfunc merge_intervals episode 19). Cause unknown; hypothesis: memory/CPU pressure from the model, Docker and WSL together. The pyfunc grader retried timeouts; this environment did not.
- Fix: a timed-out tool call is retried once (errors and floods never are); the model never sees the stalled attempt; retries are counted per episode (env.retries_used) and recorded in the baseline.
- Also recorded now: replies cut off by the 600-token limit (finish_reason == "length"), because a cut-off reply loses its closing fence or FINAL line and would look like a format error.
- Design question left open: `**FINAL:** 0.23` (markdown bold) is not recognised by the strict parser. Kept strict because the prompt names the exact form; to be decided from the counts in the real run.

## analyst baseline v1 (llama3.2:1b, temperature 0.7, 600 max tokens, 10 per task, seeds from 200000)
- Result: 1/30 passed (95% 0.01 to 0.17). mean_clean 1/10, group_median 0/10, pct_change 0/10. The run took about 2 hours.
- Endings: 23 no_final, 6 wrong_answer (5 answered on turn 1 without running code), 1 pass.
- Of the 23 no_final: 9 never sent a valid tool call, 8 got a clean tool result but never gave FINAL, 6 made tool calls but never got a clean result.
- 63 invalid replies: 38 more than one code block, 24 neither block nor FINAL, 1 bad number. The model repeated the same mistake after being told, up to 3 times.
- The model often printed "FINAL: x" from inside its own code. The environment correctly ignored it (the cheat tests require this), but the model seems to think it counts.
- Strict parser: 44 replies in 15 scoring-0 episodes contained FINAL-like text that was not accepted; under a generous reading only 1 episode would be rescued (1/30 to 2/30). Strictness is not the main cause. The one pass had a code block and a FINAL line in the same reply, and passed because FINAL wins over code.
- Tool runs: 44, of which 25 ended in the model's own errors. 7 first attempts timed out; all 7 recovered on the retry. That is about 14% of 51 launches, against roughly 1% in the pyfunc baseline. Cause unknown; untested hypotheses: memory pressure from longer conversations in Ollama, or WSL idling between calls. Without the retry, about 1 tool result in 6 would have wrongly told the model its code was too slow.
- Conclusion: works end to end with a real model; strictness is not the problem; this model is too weak at multi-turn format for a learning signal. No claim about stronger models.
- My predictions that missed: the run took 2 hours, not 1; the biggest no_final bucket was "never sent a valid tool call" (9), not "clean result but never FINAL" (8).

## analyst prompt experiment: v2 (written BEFORE the run)
- Change: prompt v2 = v1 text plus a worked example at the end (a different task, a summed price column, with a FINAL answer of 777.77, a number no real episode can have; tested over 6000 episodes) and one sentence saying FINAL is written in the reply and is never something the code prints. v1 stays the default. Tests: v2 only adds to v1; the example is valid under the parser; the prompt version does not change the episodes.
- Run: same model (llama3.2:1b), settings, seeds and tasks as baseline v1; 10 per task.
- Primary measure: passes out of 30 (v1: 1). Secondary: invalid replies per episode (v1: 2.10), no_final episodes (v1: 23), episodes that never sent a valid tool call (v1: 9).
- Prediction: 3 to 8 passes, invalid replies below 1.5 per episode, fewer than 18 no_final. If 2 passes or fewer: no meaningful change.
- Limits: with n = 30, only a large change is detectable (6 passes vs 1: Fisher p about 0.10; 8 vs 1: p about 0.03). v2 was written after reading the v1 failures on these same episodes, so this is not a held-out test, although the change is generic format guidance. Run-to-run noise at temperature 0.7 was not measured.
- Also to check afterwards: how often the model copies the example's code or its number.

## analyst prompt v2: result (llama3.2:1b, 10 per task, same seeds as v1)
- Passes 0/30 (95% 0.00 to 0.11). v1: 1/30. By the pre-registered rule (2 or fewer = no meaningful change) the primary measure did not move.
- Predictions: passes 3-8 (missed: 0); invalid replies below 1.5 per episode (missed narrowly: 1.57, v1 2.10); no_final below 18 (met: 5, v1 23).
- Endings: 25 wrong_answer (v1: 6), 5 no_final (v1: 23). Mean turns 2.5 (v1: 4.2). Tool-error rate 0.33 overall (v1: 0.57). Retries 0 (v1: 7). Cut-offs 0.
- Reading: v2 moved failures from "never answers" to "answers wrongly". Not a held-out test: v2 was written after reading the v1 failures on these same episodes. Cause of the wrong answers still unknown (next: diagnostic).
- Unexplained: the run took about 20 minutes (v1: about 2 hours), with no stalls. Fewer model calls explain only part of the speed-up. Hypothesis, untested: the machine's state differed (power settings, background load), which would also explain the stalls.

## analyst prompt v2: diagnosis
- All 25 wrong answers came from episodes where the model never sent a valid tool call. Tool runs: 3 across 30 episodes (v1: 44). Invalid replies: 45 of 47 were "neither a code block nor FINAL" (v1: 24 of 63); "more than one code block" fell from 38 to 1.
- In the transcripts the model writes code after the word "python" with no code fences, which the environment cannot run. It then guesses a FINAL number (154.56, 42.42, 2.50). Only 1 of 25 matched a known wrong approach. 0 copied the example's number or its column name. Fence line counts, v1 vs v2: __ vs __ (transcripts.txt vs transcripts_v2.txt).
- My pre-analysis guesses held: most wrong answers had no code run; few copies of the example; few wrong numbers from the model's own code.
- Correction: I suggested the drop from 7 retries to 0 meant the machine's state had changed. With only 3 tool runs in v2 it says almost nothing (at 14% per launch, P(no stall in 3 launches) is about 0.64). The speed-up (20 min vs 2 h) is more simply explained by shorter replies and fewer model calls (about 75 vs 126). Not measured per call.
- Reading (hypotheses, untested): the instruction "exactly one of these" is hard for a 1B model. The example fixed the multiple-blocks habit but the model dropped the fences, and the invalid-reply message does not say what is missing. FINAL-first behaviour may come from the example ending on a FINAL line.
- Conclusion: on llama3.2:1b both prompts give about 0 passes. v2 trades "never answers" for "answers without using the tool", which defeats the purpose of the environment. The oracle only shows the tasks are solvable by a scripted solver. Without a stronger model I cannot separate "environment too hard" from "model too weak".
- Decision: stop prompt tuning. v1 is the reported baseline; v2 is reported as an experiment, flagged as written after reading the v1 failures on the same episodes.
- Possible improvement (not made, because it changes the environment and needs new baselines): make the invalid-reply message say that code must be inside a fenced block.

## pyfunc baseline re-run (predictions written BEFORE the run)
- Same model (llama3.2:1b), settings, prompts and seeds as the 85/100 run, 20 per task. The grader has since gained a timeout retry and a recorded reason per score.
- Predictions: overall 79 to 91 passes out of 100; between 6 and 18 episodes change result between the two runs, mostly in second_largest and fizzbuzz_list; palindrome and merge_intervals stay near the ceiling; 0 to 3 episodes scored as a timeout; a handful at most with a retried timeout.
- Purpose: report numbers produced by the code as it now stands, and measure run-to-run noise.

## pyfunc baseline re-run: result (llama3.2:1b, temperature 0.7, 20 per task, same seeds and prompts as the first run)
- New run: 80/100 (95% 0.71 to 0.87). First run: 85/100 (0.77 to 0.91). Per task, first run to new run: is_palindrome 20 to 20, second_largest 11 to 8, run_length_encode 19 to 20, fizzbuzz_list 17 to 14, merge_intervals 18 to 18.
- Run-to-run noise: 23 of 100 episodes changed result (14 lost, 9 gained); 18 of the 23 were in second_largest and fizzbuzz_list. Exact sign test: p about 0.4. The two runs cannot be told apart, and differences of a few passes on one task are within noise at 20 episodes per task. The runs share their questions, so they are not independent and are not pooled.
- Predictions: 79-91 passes (met: 80); 6-18 episodes changing (missed: 23); changes mostly in second_largest and fizzbuzz_list (met); palindrome and merge_intervals near the ceiling (met); 0-3 scored as timeouts (met: 0); retried timeouts "a handful at most" (missed: 9).
- Audit of the 20 failures (audit_failures.py): all honest model errors; no NO MISMATCH FOUND. second_largest 12 (7 on the guaranteed input [1, 2], 1 on [4], 2 crashes in the model's own code, 2 other wrong values); fizzbuzz_list 6 (3 on the guaranteed input 15, 1 crash in the model's own code, 2 other wrong lists); merge_intervals 2 (IndexError, NameError in the model's own code).
- Stalls: 9 episodes had a timeout that was retried, and all 9 recovered (0 ended as a timeout). That is about 8% of episodes, 4 of the 9 passed after the retry. CORRECTION: I wrote earlier that the pyfunc rate was roughly 1%. That was one flagged episode in about 150, and stalls on replies that were wrong anyway would have been invisible to that audit. The analyst runs showed about 14%. The rate has risen since the first runs; cause unknown. Untested hypotheses: the laptop's state (power plan, memory, background load) or WSL/Docker memory use.
- Retry: the timeout retry is doing real work. Without it, up to 4 episodes would have wrongly scored 0.
- The first run's results are kept as analysis/pyfunc_baseline_before_reasons.json.

- Retry numbers (compare_baselines.py): 9 of 100 episodes (9.0%) had a first attempt that timed out and was retried (109 launches in total); 0 were still a timeout after the retry; 4 of the 9 passed. The other 5 failed on their merits.
- My guess that most of the 9 would pass was wrong (4 of 9; 95% 0.19 to 0.73, too few to say whether stalls hit slower programs more often).
- Correction: "about 8%" was 9 of 109 launches; per first attempt it is 9 of 100 (9.0%).