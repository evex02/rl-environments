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