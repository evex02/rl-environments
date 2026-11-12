# Threat model: pyfunc

## What is being protected
- **The host machine**: its files, credentials and network.
- **The answer key**: the reference solutions and input generators. They run on the host only.
- **The reward**: it should be 1.0 only for a function that really works, and 0.0 otherwise.
- **The record**: the reasons and results saved from runs.
- **Availability**: a run should not be stalled or exhausted by one bad reply.

## Who is the adversary
Code written by an AI model. It may be accidentally harmful, or it may have learned to exploit the reward during training.

It is assumed to be able to:
- run arbitrary Python inside the container;
- read and change everything in the sandboxed program, including the harness that wraps it;
- print anything, including text that imitates the grader's own output;
- exit with any exit code;
- loop forever, allocate memory, start processes, fill disk and flood output.

It is **not** assumed to be able to break out of the container. That is out of scope (see below).

## Trust boundary
- **Trusted (host):** the grader, task definitions, input generators, reference solutions, and the runner's own status logic.
- **Untrusted (container):** the model's code, and the harness text it runs inside. Everything in the container is treated as public and modifiable by the adversary.
- **What crosses the boundary:** the program text goes in over standard input. Up to 100 KB of output comes out. The answer key never goes in.

## Threats and what stops them

| # | Threat | Mitigation | Guard | Status |
|---|---|---|---|---|
| 1 | Read or change host files | No host folders are mounted; the container has its own filesystem | `test_host_files_are_not_visible` | Mitigated, tested |
| 2 | Use the network | `--network none` | `test_network_is_blocked` | Mitigated, tested |
| 3 | Write outside scratch space | Read-only root filesystem; a 16 MB `/tmp` is the only writable area | `test_cannot_write_outside_tmp`, `test_filling_tmp_is_contained` | Mitigated, tested |
| 4 | Gain privileges | Non-root user, all capabilities dropped, no-new-privileges | `test_runs_as_non_root` | Mitigated, partly tested |
| 5 | Infinite loop | Time limit inside the container, plus a host-side backstop | `test_infinite_loop_is_stopped` | Mitigated, tested |
| 6 | Memory hog | 128 MB limit, swap disabled | `test_memory_hog_is_killed` | Mitigated, tested |
| 7 | Fork bomb | Process limit of 64 | `test_fork_bomb_is_contained` | Mitigated, tested |
| 8 | Output flood | Output goes to a file inside the container; only the first 100 KB leaves; a larger output is a flood | `test_output_flood_is_cut_off` | Mitigated, tested (was a real hole: 113 s before the fix) |
| 9 | Fake a pass by exiting early or forcing a success exit code | The answer key is outside the sandbox; the exit code decides nothing | the five cheats in `test_pyfunc.py` | Mitigated, tested |
| 10 | Print the expected answers from memory | Fresh inputs every episode, answers from a reference solution run on the host; duplicate answer lines are rejected | `test_answers_memorised_from_one_episode_do_not_transfer` | Mitigated, tested |
| 11 | Tamper with the harness (patch the answer printer, read the question list) | Nothing sensitive is in the sandbox, so tampering gains nothing | `test_harness_attacks.py` | Mitigated, tested |
| 12 | Forge the failure reason by printing the runner's status text | The runner decides the status from the exit code, a byte count and a timer, in a channel separate from output | `test_program_output_cannot_spoof_the_failure_reason` | Mitigated, tested (reward was never affected, the record was) |
| 13 | Wrong solutions earn reward (weak tests) | Every episode includes inputs that test each rule in the prompt | `test_known_wrong_solution_never_earns_reward` (17 wrong solutions x 200 episodes) | Mitigated, tested, but only for wrong solutions I thought of |
| 14 | Correct solutions score 0 (false negatives) | The grader sees all output or none; timeouts are retried once; every reference solution is checked across several episodes | `test_reference_solution_passes_on_other_seeds`, `test_legitimate_output_fits_under_the_cap` | Mitigated, tested |
| 15 | Fake a timeout by exiting with code 124 | none yet | `test_exit_code_124_cannot_spoof_a_timeout` (expected failure) | **Open.** The reward is unaffected; the reason is mislabelled and grading repeats once |

## Residual risks
- **Container escape.** Docker is a strong convenience boundary, not a perfect one. Mitigations reduce the attack surface (no network, no mounts, no capabilities, non-root, throwaway containers), but a kernel-level vulnerability is out of scope. Stronger isolation (gVisor, microVMs) would be needed for hostile code at scale.
- **The grading logic is public.** The reference solutions and input generators are in this repository. The design relies on the answer key being outside the sandbox, not on secrecy. A model trained on this repository could learn the traps; the fresh inputs and reference solutions still require a working function.
- **Seed reuse.** Fresh inputs only help if seeds do not repeat. Evaluation seeds (from 100000) are kept apart from any training seeds.
- **Slow starts.** The host-side backstop timer starts before the container does. If the sandbox image has to be downloaded during a run, the delay could be reported as a timeout. CI pulls the image first.
- **Known wrong solutions only.** The false-positive tests cover the wrong solutions I thought of. New ones should be added whenever found.
- **Small sample.** One model, one prompt, 20 episodes per task. One zero in the baseline (`merge_intervals`, episode 19) passed 30/30 on re-grading and its cause is unknown.

## Rules for contributors
1. AI-written code must only ever run through `run_python_detailed`. Never run it on the host.
2. Never put answers or secrets into a program that goes into the sandbox.
3. Never take a status or reason from the program's output.
4. Reference solutions and wrong-solution lists run on the host, so they must only contain code written by a person.
5. Every new task needs a reference solution, generated inputs that test each rule in its prompt, and entries in the wrong-solution list.