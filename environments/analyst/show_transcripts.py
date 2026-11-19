import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for _folder in ("sandbox", "common"):
    sys.path.insert(0, str(ROOT / _folder))

from analyst_baseline import EVAL_SEED_START, results_path
from analyst_env import AnalystEnv
from analyst_tasks import TASKS

LIMIT = 1200  # characters shown per message


def show(text):
    text = text.strip()
    if len(text) > LIMIT:
        return text[:LIMIT] + f"\n... [{len(text) - LIMIT} more characters]"
    return text


def main():
    version = sys.argv[1] if len(sys.argv) > 1 else "v1"
    data = json.loads(results_path(version).read_text(encoding="utf-8"))
    names = [t["name"] for t in TASKS]
    lines = []
    for r in data["records"]:
        t_index = names.index(r["task"])
        env = AnalystEnv(
            seed=EVAL_SEED_START + t_index * 1000 + r["episode"],
            tasks=[TASKS[t_index]],
        )
        env.reset()
        lines.append("=" * 70)
        lines.append(
            f"{r['task']} episode {r['episode']}: reward {r['reward']} ({r['reason']}), "
            f"{r['turns']} turns, {r['tool_errors']} tool errors, "
            f"{r['invalid_replies']} invalid replies"
        )
        lines.append(
            f"true answer: {env.episode['answer']}   "
            f"wrong approaches: {env.episode['decoys']}"
        )
        for message in r["transcript"][1:]:  # message 0 is the prompt
            lines.append(f"--- {message['role']} ---")
            lines.append(show(message["content"]))
        lines.append("")
    name = "transcripts.txt" if version == "v1" else f"transcripts_{version}.txt"
    out = ROOT / "analysis" / name
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {len(data['records'])} episodes to {out}")


if __name__ == "__main__":
    main()