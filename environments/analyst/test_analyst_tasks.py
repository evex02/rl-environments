import csv
import io
import re
import statistics

import pytest

from analyst_tasks import MARGIN, TASKS, TOLERANCE, make_episode

SEEDS = range(200)
BY_NAME = {t["name"]: t for t in TASKS}


def task_id(task):
    return task["name"]


def rows_of(episode):
    return list(csv.DictReader(io.StringIO(episode["csv"])))


def test_margin_is_wider_than_the_tolerance():
    assert MARGIN > TOLERANCE


@pytest.mark.parametrize("task", TASKS, ids=task_id)
def test_same_seed_gives_the_same_episode(task):
    assert make_episode(task, 5) == make_episode(task, 5)


@pytest.mark.parametrize("task", TASKS, ids=task_id)
def test_different_seeds_give_different_data(task):
    assert make_episode(task, 1)["csv"] != make_episode(task, 2)["csv"]


@pytest.mark.parametrize("task", TASKS, ids=task_id)
def test_episode_has_the_expected_parts(task):
    ep = make_episode(task, 0)
    assert set(ep) == {"csv", "question", "answer", "decoys"}
    assert len(ep["decoys"]) >= 3
    assert round(ep["answer"], 2) == ep["answer"]


@pytest.mark.parametrize("task", TASKS, ids=task_id)
def test_no_wrong_approach_is_close_to_the_answer(task):
    for seed in SEEDS:
        ep = make_episode(task, seed)
        for name, value in ep["decoys"].items():
            assert abs(value - ep["answer"]) > MARGIN, (seed, name)


# The answer is recomputed from the CSV text the model will actually see,
# using different code from the generator.

def test_mean_clean_answer_matches_the_csv():
    task = BY_NAME["mean_clean"]
    for seed in SEEDS:
        ep = make_episode(task, seed)
        values = [float(r["reading"]) for r in rows_of(ep)]
        valid = [v for v in values if v != -999]
        assert len(values) - len(valid) >= 2  # missing values really are present
        assert round(sum(valid) / len(valid), 2) == ep["answer"]


def test_group_median_answer_matches_the_csv():
    task = BY_NAME["group_median"]
    for seed in SEEDS:
        ep = make_episode(task, seed)
        target = re.search(r"for the group `(\w+)`", ep["question"]).group(1)
        values = [float(r["value"]) for r in rows_of(ep) if r["group"] == target]
        assert len(values) % 2 == 0
        assert round(statistics.median(values), 2) == ep["answer"]


def test_pct_change_answer_matches_the_csv():
    task = BY_NAME["pct_change"]
    for seed in SEEDS:
        ep = make_episode(task, seed)
        first, second = re.findall(r"`(\d{4}-\d{2})`", ep["question"])
        totals = {}
        for r in rows_of(ep):
            totals[r["month"]] = totals.get(r["month"], 0.0) + float(r["amount"])
        want = round((totals[second] - totals[first]) / totals[first] * 100, 2)
        assert abs(want - ep["answer"]) < 0.011