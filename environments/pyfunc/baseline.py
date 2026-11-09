import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scratch"))

from openai import OpenAI

from grader import extract_code
from pyfunc_env import PyFuncEnv
from stats_utils import wilson_interval
from tasks import TASKS

TEMPERATURE = 0.7
MAX_TOKENS = 600
EVAL_SEED_START = 100_000  # evaluation seeds; keep training seeds elsewhere


def summarise(records):
    """Per-task and overall pass rates with 95% intervals."""
    groups = {}
    for r in records:
        groups.setdefault(r["task"], []).append(r)
    groups["ALL"] = list(records)
    summary = {}
    for name, rows in groups.items():
        n = len(rows)
        passes = sum(1 for r in rows if r["reward"] == 1.0)
        with_code = sum(1 for r in rows if r["has_code"])
        low, high = wilson_interval(passes, n)
        summary[name] = {
            "n": n,
            "pass_rate": passes / n,
            "low": low,
            "high": high,
            "code_block_rate": with_code / n,
        }
    return summary


def ask_model(client, model, prompt):
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
    )
    return response.choices[0].message.content or ""


def save_results(model, episodes, records):
    out = ROOT / "analysis" / "pyfunc_baseline.json"
    out.parent.mkdir(exist_ok=True)
    data = {
        "model": model,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "episodes_per_task": episodes,
        "summary": summarise(records),
        "records": records,
    }
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")


def main():
    episodes = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    model = sys.argv[2] if len(sys.argv) > 2 else "llama3.2:1b"
    client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama", timeout=300)

    records = []
    for t_index, task in enumerate(TASKS):
        for i in range(episodes):
            env = PyFuncEnv(seed=EVAL_SEED_START + t_index * 1000 + i, tasks=[task])
            prompt = env.reset()
            reply = ask_model(client, model, prompt)
            reward = env.step(reply)
            records.append(
                {
                    "task": task["name"],
                    "episode": i,
                    "reward": reward,
                    "has_code": extract_code(reply) is not None,
                    "reply": reply,
                }
            )
            print(f"{task['name']} {i + 1}/{episodes}: reward {reward}", flush=True)
            save_results(model, episodes, records)

    print()
    print(f"model: {model}, {episodes} episodes per task")
    for name, s in summarise(records).items():
        print(
            f"{name:20s} pass {s['pass_rate']:.2f} "
            f"(95% {s['low']:.2f} to {s['high']:.2f}) | "
            f"code block {s['code_block_rate']:.2f} | n={s['n']}"
        )


if __name__ == "__main__":
    main()