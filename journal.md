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