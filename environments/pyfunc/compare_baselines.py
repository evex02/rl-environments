import json
import sys
from collections import Counter
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for _folder in ("sandbox", "common"):
    sys.path.insert(0, str(ROOT / _folder))

from stats_utils import wilson_interval

OLD = "pyfunc_baseline_before_reasons.json"
NEW = "pyfunc_baseline.json"


def load(name):
    path = ROOT / "analysis" / name
    data = json.loads(path.read_text(encoding="utf-8"))
    return {(r["task"], r["episode"]): r for r in data["records"]}


def passed(record):
    return record["reward"] == 1.0


def sign_test_p(lost, gained):
    """Exact two-sided sign test: if nothing real changed, results that flip are
    equally likely to go either way."""
    n = lost + gained
    if n == 0:
        return 1.0
    k = min(lost, gained)
    tail = sum(comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * tail)


def main():
    old, new = load(OLD), load(NEW)
    keys = [k for k in new if k in old]
    tasks = list(dict.fromkeys(k[0] for k in keys))

    print("Same model, settings, prompts and seeds. Differences are sampling noise")
    print("(temperature 0.7) plus the timeout retry added since the first run.\n")
    print(f"{'task':20s} {'old':>4s} {'new':>4s} {'lost':>5s} {'gained':>7s}")
    totals = {"old": 0, "new": 0, "lost": 0, "gained": 0}
    for task in tasks:
        ks = [k for k in keys if k[0] == task]
        o = sum(passed(old[k]) for k in ks)
        n = sum(passed(new[k]) for k in ks)
        lost = sum(passed(old[k]) and not passed(new[k]) for k in ks)
        gained = sum(passed(new[k]) and not passed(old[k]) for k in ks)
        print(f"{task:20s} {o:4d} {n:4d} {lost:5d} {gained:7d}")
        totals["old"] += o
        totals["new"] += n
        totals["lost"] += lost
        totals["gained"] += gained

    total = len(keys)
    print(
        f"{'ALL':20s} {totals['old']:4d} {totals['new']:4d} "
        f"{totals['lost']:5d} {totals['gained']:7d}"
    )
    print("(lost = passed in the old run, failed in the new; gained = the reverse)\n")
    for label in ("old", "new"):
        low, high = wilson_interval(totals[label], total)
        print(f"{label}: {totals[label]}/{total} (95% {low:.2f} to {high:.2f})")
    flipped = totals["lost"] + totals["gained"]
    print(f"\nEpisodes whose result changed between the two runs: {flipped} of {total}")
    p = sign_test_p(totals["lost"], totals["gained"])
    print(f"Exact sign test on {totals['lost']} lost vs {totals['gained']} gained: p = {p:.2f}")

    records = list(new.values())
    reasons = Counter(r.get("reason") for r in records)
    print(f"\nReasons in the new run: {dict(reasons)}")

    graded = [r for r in records if r.get("attempts", 0) >= 1]
    retried = [r for r in graded if r["attempts"] > 1]
    launches = sum(r["attempts"] for r in graded)
    rescued = sum(passed(r) for r in retried)
    print(f"\nEpisodes that reached the sandbox: {len(graded)}; launches in total: {launches}")
    print(
        f"First attempts that timed out and were retried: {len(retried)} "
        f"({len(retried) / len(graded):.1%} of episodes)"
    )
    print(f"  of those, still a timeout after the retry: {sum(r['reason'] == 'timeout' for r in retried)}")
    print(f"  of those, passed after the retry: {rescued}")
    print(f"  (without the retry, up to {rescued} episodes would have scored 0)")


if __name__ == "__main__":
    main()