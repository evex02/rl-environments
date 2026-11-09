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