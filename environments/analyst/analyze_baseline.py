import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for _folder in ("sandbox", "common"):
    sys.path.insert(0, str(ROOT / _folder))

from analyst_baseline import EVAL_SEED_START, results_path
from analyst_env import EXAMPLE_ANSWER, AnalystEnv
from analyst_parsing import parse_reply
from analyst_tasks import TASKS, TOLERANCE

# A deliberately generous reading of "FINAL ... <number>". It is used only to
# ask how often the strict parser cost the model a reward. It never scores anything.
LENIENT_FINAL = re.compile(
    r"final[^0-9\n+-]{0,12}([+-]?\d[\d,]*\.?\d*|[+-]?\.\d+)", re.IGNORECASE
)
NUMBER = re.compile(r"[+-]?\d+(?:\.\d+)?")


def lenient_value(reply):
    matches = LENIENT_FINAL.findall(reply)
    if not matches:
        return None
    try:
        return float(matches[0].replace(",", ""))
    except ValueError:
        return None


def last_tool_number(feedback):
    """The last number in the most recent clean tool output, or None."""
    for text in reversed(feedback):
        if text.startswith("TOOL OUTPUT:") and "Traceback" not in text:
            body = text[len("TOOL OUTPUT:"):].split("\n\nYou have")[0]
            numbers = NUMBER.findall(body)
            return float(numbers[-1]) if numbers else None
    return None


def main():
    version = sys.argv[1] if len(sys.argv) > 1 else "v1"
    data = json.loads(results_path(version).read_text(encoding="utf-8"))
    names = [t["name"] for t in TASKS]

    no_final_kinds = Counter()
    invalid_rules = Counter()
    wrong_kinds = Counter()
    decoy_matches = Counter()
    near_miss_replies = near_miss_episodes = rescued = 0
    retries = persisted = tool_runs = tool_errors = 0
    price_key_errors = copied_example_code = 0

    for r in data["records"]:
        t_index = names.index(r["task"])
        env = AnalystEnv(
            seed=EVAL_SEED_START + t_index * 1000 + r["episode"],
            tasks=[TASKS[t_index]],
        )
        env.reset()
        truth = env.episode["answer"]
        decoys = env.episode["decoys"]

        replies = [m["content"] for m in r["transcript"] if m["role"] == "assistant"]
        feedback = [m["content"] for m in r["transcript"][1:] if m["role"] == "user"]
        parsed = [parse_reply(x) for x in replies]
        kinds = [p[0] for p in parsed]

        retries += r.get("retries", 0)
        tool_runs += r["tool_runs"]
        tool_errors += r["tool_errors"]
        persisted += sum("ran out of time" in f for f in feedback)
        price_key_errors += any("KeyError: 'price'" in f for f in feedback)
        copied_example_code += any("r['price']" in x for x in replies)
        for kind, detail in parsed:
            if kind == "invalid":
                invalid_rules[detail] += 1

        if r["reason"] == "wrong_answer":
            final_value = parsed[-1][1]
            ran_code = "tool" in kinds[:-1]
            if abs(final_value - EXAMPLE_ANSWER) <= 0.01:
                wrong_kinds["copied the example's number"] += 1
            elif not ran_code:
                wrong_kinds["answered without running any code"] += 1
            else:
                seen = last_tool_number(feedback)
                if seen is not None and abs(seen - final_value) <= 0.011:
                    wrong_kinds["ran code, then reported the number it printed (wrong)"] += 1
                else:
                    wrong_kinds["ran code, but answered with a different number"] += 1
            for name, value in decoys.items():
                if abs(value - final_value) <= TOLERANCE + 1e-9:
                    decoy_matches[name] += 1

        if r["reason"] == "no_final":
            clean_result = any(
                f.startswith("TOOL OUTPUT:") and "Traceback" not in f for f in feedback
            )
            if kinds.count("tool") == 0:
                no_final_kinds["never sent a valid tool call"] += 1
            elif clean_result:
                no_final_kinds["got a clean result but never gave FINAL"] += 1
            else:
                no_final_kinds["tool calls, but never a clean result"] += 1

        if r["reward"] == 0.0:
            values = [
                lenient_value(x) for x, kind in zip(replies, kinds) if kind != "final"
            ]
            values = [v for v in values if v is not None]
            near_miss_replies += len(values)
            if values:
                near_miss_episodes += 1
                if abs(values[0] - truth) <= TOLERANCE + 1e-9:
                    rescued += 1

    print(f"prompt {version}: {len(data['records'])} episodes\n")
    print("Wrong final answers, by what the model did:")
    for name, count in wrong_kinds.most_common():
        print(f"  {count:3d}  {name}")
    print("  Wrong answers that matched a known wrong approach:", dict(decoy_matches))
    print("\nEpisodes that ended without a FINAL answer, by what the model did:")
    for name, count in no_final_kinds.most_common():
        print(f"  {count:3d}  {name}")
    print("\nInvalid replies, by the rule broken:", dict(invalid_rules))
    print(
        f"\nSigns of copying the example: {copied_example_code} episodes used its column "
        f"name in code, {price_key_errors} hit KeyError: 'price'"
    )
    print(
        f"\nStrict-parser near misses: {near_miss_replies} replies in {near_miss_episodes} "
        "scoring-0 episodes contained FINAL-like text that was not accepted."
    )
    print(f"  In how many of those episodes the first such number matched the truth: {rescued}")
    print(f"\nTool runs: {tool_runs}; ending in an error or timeout: {tool_errors}")
    print(
        f"Timeout retries: {retries}; still timed out after the retry: {persisted}; "
        f"recovered by the retry: {retries - persisted}"
    )


if __name__ == "__main__":
    main()