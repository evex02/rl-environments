import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scratch"))

from baseline import EVAL_SEED_START
from grader import build_program, extract_code, make_episode, parse_results
from pyfunc_env import PyFuncEnv
from run_code_docker import MAX_OUTPUT_BYTES, run_python_sandboxed
from tasks import TASKS


def explain(record):
    """Re-run one failing reply and say why it scored 0."""
    names = [t["name"] for t in TASKS]
    t_index = names.index(record["task"])
    task = TASKS[t_index]

    # Rebuild the exact episode the baseline used.
    seed = EVAL_SEED_START + t_index * 1000 + record["episode"]
    env = PyFuncEnv(seed=seed, tasks=[task])
    env.reset()
    inputs, expected = make_episode(task, env.episode_seed)

    code = extract_code(record["reply"])
    if code is None:
        return "no code block in the reply"
    _ok, output = run_python_sandboxed(
        build_program(code, task, inputs),
        timeout=5,
        keep_chars=MAX_OUTPUT_BYTES,
    )
    results = parse_results(output)
    if results is None:
        return "the same question was answered twice"
    if len(results) != len(expected):
        return (
            f"got {len(results)} answers, expected {len(expected)}. "
            f"End of output:\n{output[-400:]}"
        )
    for index, want in enumerate(expected):
        got = results.get(index)
        if got != want:
            return f"input {inputs[index]!r}: expected {want}, got {got}"
    return "NO MISMATCH FOUND: scored 0.0 but every answer matches. Possible grader bug!"


def main():
    path = ROOT / "analysis" / "pyfunc_baseline.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    failures = [r for r in data["records"] if r["reward"] == 0.0]
    print(f"{len(failures)} failing replies\n")
    for r in failures:
        print(f"== {r['task']} episode {r['episode']}")
        print(explain(r))
        print()


if __name__ == "__main__":
    main()