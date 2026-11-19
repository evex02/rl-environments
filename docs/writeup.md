# What I learned building two RL environments, and then trying to break them

This is a learning project: two environments for reinforcement learning on language models (`pyfunc`, where the model writes a function, and `analyst`, a multi-turn tool-use task), a Docker sandbox for untrusted code, and a large set of tests that attack my own reward functions. I have not trained a model on them. I evaluated them with one small local model, llama3.2:1b, so everything below is about how the environments behave, not about what a trained model can do.


## Five things I learned

**1. A reward can be wrong in two directions, and at first I only checked one.** Rewards that are too generous: plausible wrong palindrome solutions earned full marks in 39% to 80% of episodes, because my generator built its "palindromes" by exact mirroring and so rarely tested the case, punctuation and digit rules. In `analyst`, skipping the first or last data row earned reward in 18% and 23% of episodes, because the skipped row was often a missing value that did not count anyway. Rewards that are too harsh: a correct FizzBuzz answer scored 0 because the sandbox cut its output at 2000 characters. The fixes were the same in spirit: guarantee that every episode contains inputs that test each rule, and check the reward against both wrong and correct solutions.

**2. Everything inside the sandbox is public to the model.** The answer key never enters it. Early on the grader decided success from an exit code that the model's own code could set, so exiting early earned reward 1.0. Once the answer key moved to the host and the sandbox only printed its answers, those cheats stopped working. A later attack could not change the reward but could forge the recorded *reason* for a failure, by printing the runner's own status text, so status now travels in a separate channel from program output.

**3. An attack test proves nothing until I have seen the attack succeed.** My first "memorised answers" cheat passed the test I wanted to see fail, because the program exited before its output buffer was flushed and the fake answers were lost. Fixing the attack showed the hole was real. Since then every attack test has a control: a planted marker the search should find, a task with a constant answer that the blind-guessing measure must flag, and a correct solver that must score 1.0.

**4. A green test run can hide skipped tests.** One run reported 93 passed and 31 skipped, which looked mostly fine and had verified almost none of the sandbox, because Docker was not running. The test setup now waits for Docker, and a strict mode makes a missing Docker stop the run.

**5. Measure the noise before reading a difference.** I ran the same model on the same 100 `pyfunc` questions twice. It scored 85 and then 80, and 23 of the 100 episodes changed result (exact sign test p of about 0.4). So a difference of a few passes on one task is not a finding. On `analyst`, a second prompt cut episodes with no valid answer from 23 to 5, which is far outside that noise, but it also made the model stop using the tool, so I rejected it.

## My predictions, and how they did

I wrote predictions down before several runs, and the journal records them. Wrong: I expected the second prompt to give 3 to 8 passes (it gave 0), expected 6 to 18 episodes to change between identical runs (23 did), and guessed two hours for a run I thought would take one. Right: I predicted which tests would fail at each red-team step, that a correct FizzBuzz answer would be punished by the output limit, and that most wrong `analyst` answers would come from replies that never ran code.

## What this does not show

- No training run. I have not shown either reward is learnable, or that it holds up under optimisation pressure.
- One small model. `analyst` is too hard for it (1 pass in 30), and two `pyfunc` tasks are at its ceiling, so neither environment is calibrated for it.
- About 9% of `pyfunc` episodes in the re-run had a harmless program time out and then pass on retry. I do not know why.
- One zero in the first baseline (`merge_intervals`, episode 19) passed 30 out of 30 when re-graded, and I never found the cause.
- `analyst` has attack tests but no standalone threat model, and the sandbox relies on Docker, which is not a perfect security boundary.

## What I would do next

Run both environments against a stronger model, so there is a difficulty range to learn from. Write the `analyst` threat model. Measure run-to-run noise on `analyst` and find the cause of the stalls. Then try a small training run on free GPU, which is the thing this project was meant to lead to.