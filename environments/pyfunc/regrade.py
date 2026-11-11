import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scratch"))

from baseline import EVAL_SEED_START
from grader import build_program, extract_code, make_episode, parse_results
from pyfunc_env import PyFuncEnv
from run_code_docker import MAX_OUTPUT_BYTES, run_python_sandboxed
from tasks import TASKS


def classify(output, expected):
    """Say what happened in one sandbox run."""
    if output == "timed out":
        return "TIMED OUT"
    if output == "output limit exceeded":
        return "FLOOD"
    results = parse_results(output)
    if results is None:
        return "DUPLICATE ANSWERS"
    if len(results) != len(expected):
        return "WRONG ANSWER COUNT"
    for index, want in enumerate(expected):
        if results.get(index) != want:
            return "MISMATCH"
    return "PASS"


def main():
    task_name = sys.argv[1]
    episode = int(sys.argv[2])
    repeats = int(sys.argv[3]) if len(sys.argv) > 3 else 30

    path = ROOT / "analysis" / "pyfunc_baseline.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    record = next(
        r for r in data["records"] if r["task"] == task_name and r["episode"] == episode
    )

    names = [t["name"] for t in TASKS]
    t_index = names.index(task_name)
    task = TASKS[t_index]
    seed = EVAL_SEED_START + t_index * 1000 + episode
    env = PyFuncEnv(seed=seed, tasks=[task])
    env.reset()
    inputs, expected = make_episode(task, env.episode_seed)

    code = extract_code(record["reply"])
    print("--- the model's code ---")
    print(code)
    print("--- end of code ---\n")

    program = build_program(code, task, inputs)
    counts = Counter()
    for i in range(repeats):
        start = time.time()
        _ok, output = run_python_sandboxed(
            program, timeout=5, keep_chars=MAX_OUTPUT_BYTES
        )
        seconds = time.time() - start
        verdict = classify(output, expected)
        counts[verdict] += 1
        print(f"run {i + 1}/{repeats}: {verdict} in {seconds:.1f}s", flush=True)
        if verdict != "PASS":
            print("   output ends:", output[-300:].replace("\n", " | "))
    print()
    print(dict(counts))


if __name__ == "__main__":
    main()