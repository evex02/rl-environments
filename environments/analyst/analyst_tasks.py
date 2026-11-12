import random
import statistics

TOLERANCE = 0.01  # answers are compared to 2 decimal places
MARGIN = 0.05     # generators reject data where a wrong approach lands this close


def _csv(header, rows):
    lines = [",".join(header)]
    lines += [",".join(str(cell) for cell in row) for row in rows]
    return "\n".join(lines) + "\n"


def _separated(answer, decoys):
    """True if every wrong approach is clearly different from the answer."""
    return all(abs(value - answer) > MARGIN for value in decoys.values())


def _mean_clean(rng):
    while True:
        n = rng.randint(12, 20)
        holes = set(rng.sample(range(n), rng.randint(2, 4)))
        values = [
            -999 if i in holes else round(rng.uniform(10, 50), 1) for i in range(n)
        ]
        valid = [v for v in values if v != -999]
        answer = round(sum(valid) / len(valid), 2)
        decoys = {
            "mean_of_all_rows": round(sum(values) / n, 2),
            "missing_as_zero": round(sum(valid) / n, 2),
            "median_of_valid": round(statistics.median(valid), 2),
        }
        if _separated(answer, decoys):
            break
    rows = [(i + 1, v) for i, v in enumerate(values)]
    return {
        "csv": _csv(("id", "reading"), rows),
        "question": (
            "What is the mean of the valid readings in the `reading` column? "
            "A value of -999 means the reading is missing and must be left out. "
            "Give the answer to 2 decimal places."
        ),
        "answer": answer,
        "decoys": decoys,
    }


GROUP_BASES = {"north": 20, "south": 40, "east": 60}


def _group_median(rng):
    while True:
        values = {}
        for name, base in GROUP_BASES.items():
            size = rng.randint(7, 11)
            values[name] = [
                round(rng.uniform(base - 10, base + 10), 1) for _ in range(size)
            ]
        # The target group has an even number of rows and two big outliers.
        target = rng.choice(list(GROUP_BASES))
        base = GROUP_BASES[target]
        size = rng.choice([8, 10])
        normal = [round(rng.uniform(base - 10, base + 10), 1) for _ in range(size - 2)]
        outliers = [round(rng.uniform(150, 200), 1) for _ in range(2)]
        values[target] = normal + outliers

        ordered = sorted(values[target])
        mid = len(ordered) // 2
        if ordered[mid] - ordered[mid - 1] < 1.0:
            continue  # the two middle values must differ, so picking one is wrong

        answer = round(statistics.median(ordered), 2)
        everything = [v for group in values.values() for v in group]
        decoys = {
            "mean_of_group": round(statistics.mean(ordered), 2),
            "median_of_all_rows": round(statistics.median(everything), 2),
            "upper_middle_value": round(ordered[mid], 2),
            "lower_middle_value": round(ordered[mid - 1], 2),
        }
        for other in GROUP_BASES:
            if other != target:
                decoys[f"median_of_{other}"] = round(statistics.median(values[other]), 2)
        if _separated(answer, decoys):
            break
    rows = [(name, v) for name, group in values.items() for v in group]
    rng.shuffle(rows)
    return {
        "csv": _csv(("group", "value"), rows),
        "question": (
            "The table has columns `group` and `value`. What is the median "
            f"`value` for the group `{target}`? Give the answer to 2 decimal places."
        ),
        "answer": answer,
        "decoys": decoys,
    }


MONTHS = ["2025-01", "2025-02", "2025-03", "2025-04"]


def _pct_change(rng):
    while True:
        amounts = {
            m: [round(rng.uniform(10, 100), 1) for _ in range(rng.randint(3, 6))]
            for m in MONTHS
        }
        first, second = rng.sample(MONTHS, 2)
        if len(amounts[first]) == len(amounts[second]):
            continue  # equal row counts would make "average" and "total" agree
        rows = [(m, a) for m, group in amounts.items() for a in group]
        rng.shuffle(rows)

        total_1, total_2 = sum(amounts[first]), sum(amounts[second])
        answer = round((total_2 - total_1) / total_1 * 100, 2)
        first_row = {}
        for month, amount in rows:
            first_row.setdefault(month, amount)
        mean_1 = total_1 / len(amounts[first])
        mean_2 = total_2 / len(amounts[second])
        decoys = {
            "change_in_averages": round((mean_2 - mean_1) / mean_1 * 100, 2),
            "first_row_only": round(
                (first_row[second] - first_row[first]) / first_row[first] * 100, 2
            ),
            "divided_by_new_total": round((total_2 - total_1) / total_2 * 100, 2),
            "wrong_direction": round((total_1 - total_2) / total_1 * 100, 2),
            "ratio_without_subtracting_one": round(total_2 / total_1 * 100, 2),
        }
        if _separated(answer, decoys):
            break
    return {
        "csv": _csv(("month", "amount"), rows),
        "question": (
            "The table has columns `month` and `amount`. What is the percent "
            f"change in the total `amount` from month `{first}` to month `{second}`? "
            f"Use (total in {second} - total in {first}) / total in {first} * 100. "
            "Give the answer to 2 decimal places, without a % sign."
        ),
        "answer": answer,
        "decoys": decoys,
    }


TASKS = [
    {"name": "mean_clean", "make": _mean_clean},
    {"name": "group_median", "make": _group_median},
    {"name": "pct_change", "make": _pct_change},
]


def make_episode(task, seed):
    """Build one episode from a seed: data, question, true answer, wrong answers."""
    return task["make"](random.Random(seed))