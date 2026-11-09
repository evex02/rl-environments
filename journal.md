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