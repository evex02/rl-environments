import pytest

from analyst_audit import INDEPENDENT_DECOYS, NEW_WRONG, hit_counts
from analyst_tasks import TASKS, make_episode

SEEDS = range(200)
AUDIT_SEEDS = range(500)
ALLOWED_HITS = 1  # out of 500 episodes: a coincidence, not a pattern


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t["name"])
def test_independent_versions_of_the_decoys_agree_with_the_generator(task):
    compute = INDEPENDENT_DECOYS[task["name"]]
    for seed in SEEDS:
        episode = make_episode(task, seed)
        mine = compute(episode["csv"], episode["question"])
        for name, value in episode["decoys"].items():
            assert name in mine, (seed, name)
            assert abs(mine[name] - value) <= 0.011, (seed, name)


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t["name"])
def test_independent_decoys_never_land_within_tolerance(task):
    compute = INDEPENDENT_DECOYS[task["name"]]
    counts = hit_counts(task, compute, SEEDS)
    assert all(hits == 0 for hits in counts.values()), counts


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t["name"])
def test_additional_wrong_approaches_rarely_land_within_tolerance(task):
    compute = NEW_WRONG[task["name"]]
    counts = hit_counts(task, compute, AUDIT_SEEDS)
    offenders = {name: hits for name, hits in counts.items() if hits > ALLOWED_HITS}
    assert not offenders, offenders


def test_the_hit_counter_detects_a_correct_method():
    task = next(t for t in TASKS if t["name"] == "mean_clean")

    def correct(csv_text, question):
        values = [float(line.split(",")[1]) for line in csv_text.splitlines()[1:]]
        valid = [v for v in values if v != -999]
        return {"correct": round(sum(valid) / len(valid), 2)}

    assert hit_counts(task, correct, range(50)) == {"correct": 50}