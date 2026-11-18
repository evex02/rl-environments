import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for _folder in ("sandbox", "common"):
    sys.path.insert(0, str(ROOT / _folder))

from openai import OpenAI

from analyst_env import AnalystEnv
from analyst_tasks import TASKS
from stats_utils import wilson_interval

TEMPERATURE = 0.7
MAX_TOKENS = 600
# Evaluation seeds: kept apart from pyfunc's (100000...) and from any training seeds.
EVAL_SEED_START = 200_000


def results_path(version):
    """Each prompt version saves to its own file, so one run cannot overwrite another."""
    name = "analyst_baseline.json" if version == "v1" else f"analyst_baseline_prompt_{version}.json"
    return ROOT / "analysis" / name


def summarise(records):
    """Per-task and overall results, with 95% intervals and diagnostics."""
    groups = {}
    for r in records:
        groups.setdefault(r["task"], []).append(r)
    groups["ALL"] = list(records)
    summary = {}
    for name, rows in groups.items():
        n = len(rows)
        passes = sum(1 for r in rows if r["reward"] == 1.0)
        low, high = wilson_interval(passes, n)
        runs = sum(r["tool_runs"] for r in rows)
        errors = sum(r["tool_errors"] for r in rows)
        summary[name] = {
            "n": n,
            "pass_rate": passes / n,
            "low": low,
            "high": high,
            "reasons": dict(Counter(r["reason"] for r in rows)),
            "mean_turns": sum(r["turns"] for r in rows) / n,
            "tool_error_rate": (errors / runs) if runs else 0.0,
            "invalid_per_episode": sum(r["invalid_replies"] for r in rows) / n,
            "retries": sum(r.get("retries", 0) for r in rows),
            "cut_offs": sum(r.get("cut_offs", 0) for r in rows),
        }
    return summary


def play_episode(client, model, env):
    """Play one full episode as a conversation.

    Returns (reward, info, messages, cut_offs), where cut_offs is how many of
    the model's replies stopped because they hit the token limit.
    """
    prompt = env.reset()
    messages = [{"role": "user", "content": prompt}]
    cut_offs = 0
    while True:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        choice = response.choices[0]
        reply = choice.message.content or ""
        if choice.finish_reason == "length":
            cut_offs += 1
        messages.append({"role": "assistant", "content": reply})
        observation, reward, terminated, truncated, info = env.step(reply)
        if terminated or truncated:
            return reward, info, messages, cut_offs
        messages.append({"role": "user", "content": observation})


def save_results(model, episodes, version, records):
    out = results_path(version)
    out.parent.mkdir(exist_ok=True)
    data = {
        "model": model,
        "prompt_version": version,
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
    version = sys.argv[3] if len(sys.argv) > 3 else "v1"
    client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama", timeout=300)

    records = []
    for t_index, task in enumerate(TASKS):
        for i in range(episodes):
            env = AnalystEnv(
                seed=EVAL_SEED_START + t_index * 1000 + i,
                tasks=[task],
                prompt_version=version,
            )
            reward, info, transcript, cut_offs = play_episode(client, model, env)
            records.append(
                {
                    "task": task["name"],
                    "episode": i,
                    "reward": reward,
                    **info,
                    "retries": env.retries_used,
                    "cut_offs": cut_offs,
                    "transcript": transcript,
                }
            )
            print(
                f"{task['name']} {i + 1}/{episodes}: reward {reward} "
                f"({info['reason']}, {info['turns']} turns)",
                flush=True,
            )
            save_results(model, episodes, version, records)

    print()
    print(f"model: {model}, prompt {version}, {episodes} episodes per task")
    for name, s in summarise(records).items():
        print(
            f"{name:13s} pass {s['pass_rate']:.2f} (95% {s['low']:.2f} to {s['high']:.2f}) | "
            f"turns {s['mean_turns']:.1f} | tool errors {s['tool_error_rate']:.2f} | "
            f"invalid per episode {s['invalid_per_episode']:.2f} | "
            f"retries {s['retries']} | cut off {s['cut_offs']} | {s['reasons']}"
        )


if __name__ == "__main__":
    main()