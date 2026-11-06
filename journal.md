## Project Journal
- Week 1: Installed tools and cloned the repo

## Exploit found: retry guessing
- What: the AI could answer repeatedly in one episode until correct.
- How I found it: I did it by accident while playing the environment.
- Fix: the episode ends after one reply (test: test_cannot_answer_twice_in_one_episode).