import csv
import io
import re
import statistics

from analyst_tasks import TASKS, TOLERANCE, make_episode

# Wrong approaches, written separately from the generators. They only read the
# CSV text and the question. They run on the host, so this file must only ever
# contain code written by a person. Never put AI-written code in here.


def _rows(csv_text):
    return list(csv.DictReader(io.StringIO(csv_text)))


def _whole(total):
    """Round to a whole number. Cleaning to one decimal first keeps
    floating-point noise from flipping a total that is exactly x.5."""
    return round(round(total, 1))


# --- mean_clean ---

def _readings(csv_text):
    return [float(r["reading"]) for r in _rows(csv_text)]


def mean_clean_decoys(csv_text, question):
    values = _readings(csv_text)
    valid = [v for v in values if v != -999]
    return {
        "mean_of_all_rows": round(sum(values) / len(values), 2),
        "missing_as_zero": round(sum(valid) / len(values), 2),
        "median_of_valid": round(statistics.median(valid), 2),
        "skips_first_data_row": round(
            statistics.mean([v for v in values[1:] if v != -999]), 2
        ),
        "skips_last_data_row": round(
            statistics.mean([v for v in values[:-1] if v != -999]), 2
        ),
    }


def mean_clean_new(csv_text, question):
    values = _readings(csv_text)
    valid = [v for v in values if v != -999]
    return {
        "divides_by_n_minus_1": round(sum(valid) / (len(valid) - 1), 2),
        "truncates_each_value": round(statistics.mean(int(v) for v in valid), 2),
    }


# --- group_median ---

def _group_data(csv_text, question):
    target = re.search(r"for the group `(\w+)`", question).group(1)
    groups = {}
    for r in _rows(csv_text):
        groups.setdefault(r["group"], []).append(float(r["value"]))
    return target, groups


def group_median_decoys(csv_text, question):
    target, groups = _group_data(csv_text, question)
    ordered = sorted(groups[target])
    mid = len(ordered) // 2
    everything = [v for values in groups.values() for v in values]
    decoys = {
        "mean_of_group": round(statistics.mean(ordered), 2),
        "median_of_all_rows": round(statistics.median(everything), 2),
        "upper_middle_value": round(ordered[mid], 2),
        "lower_middle_value": round(ordered[mid - 1], 2),
    }
    for name, values in groups.items():
        if name != target:
            decoys[f"median_of_{name}"] = round(statistics.median(values), 2)
    return decoys


def group_median_new(csv_text, question):
    target, groups = _group_data(csv_text, question)
    values = groups[target]
    ordered = sorted(values)
    return {
        "drops_the_two_largest": round(statistics.median(ordered[:-2]), 2),
        "midrange": round((min(values) + max(values)) / 2, 2),
        "first_value_in_file": round(values[0], 2),
    }


# --- pct_change ---

def _month_data(csv_text, question):
    first, second = re.findall(r"`(\d{4}-\d{2})`", question)
    amounts = {}
    for r in _rows(csv_text):
        amounts.setdefault(r["month"], []).append(float(r["amount"]))
    return first, second, amounts


def pct_change_decoys(csv_text, question):
    first, second, amounts = _month_data(csv_text, question)
    t1, t2 = sum(amounts[first]), sum(amounts[second])
    m1, m2 = t1 / len(amounts[first]), t2 / len(amounts[second])
    f1, f2 = amounts[first][0], amounts[second][0]
    return {
        "change_in_averages": round((m2 - m1) / m1 * 100, 2),
        "first_row_only": round((f2 - f1) / f1 * 100, 2),
        "divided_by_new_total": round((t2 - t1) / t2 * 100, 2),
        "wrong_direction": round((t1 - t2) / t1 * 100, 2),
        "ratio_without_subtracting_one": round(t2 / t1 * 100, 2),
        "totals_rounded_to_whole_numbers": round(
            (_whole(t2) - _whole(t1)) / _whole(t1) * 100, 2
        ),
    }


def pct_change_new(csv_text, question):
    first, second, amounts = _month_data(csv_text, question)
    t1, t2 = sum(amounts[first]), sum(amounts[second])
    d1, d2 = statistics.median(amounts[first]), statistics.median(amounts[second])
    return {
        "absolute_change": round(t2 - t1, 2),
        "change_in_medians": round((d2 - d1) / d1 * 100, 2),
    }


INDEPENDENT_DECOYS = {
    "mean_clean": mean_clean_decoys,
    "group_median": group_median_decoys,
    "pct_change": pct_change_decoys,
}

NEW_WRONG = {
    "mean_clean": mean_clean_new,
    "group_median": group_median_new,
    "pct_change": pct_change_new,
}


def hit_counts(task, compute, seeds):
    """For each wrong approach, in how many episodes does it land within
    tolerance of the true answer?"""
    counts = {}
    for seed in seeds:
        episode = make_episode(task, seed)
        values = compute(episode["csv"], episode["question"])
        for name, value in values.items():
            counts.setdefault(name, 0)
            if abs(value - episode["answer"]) <= TOLERANCE + 1e-9:
                counts[name] += 1
    return counts


def main():
    seeds = range(500)
    print(f"Episodes where a wrong approach lands within {TOLERANCE} of the true answer")
    print(f"(out of {len(seeds)})\n")
    for task in TASKS:
        for label, table in (("known", INDEPENDENT_DECOYS), ("additional", NEW_WRONG)):
            counts = hit_counts(task, table[task["name"]], seeds)
            for name, hits in counts.items():
                print(f"{task['name']:13s} {label:11s} {name:33s} {hits:3d}/{len(seeds)}")
        print()


if __name__ == "__main__":
    main()