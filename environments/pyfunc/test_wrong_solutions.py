import pytest

from audit_wrong_solutions import WRONG, passes_episode
from tasks import TASKS

EPISODES = 200
BY_NAME = {t["name"]: t for t in TASKS}
CASES = [(name, label) for name, solutions in WRONG.items() for label in solutions]


@pytest.mark.parametrize("name,label", CASES)
def test_known_wrong_solution_never_earns_reward(name, label):
    task = BY_NAME[name]
    namespace = {}
    exec(WRONG[name][label], namespace)  # our own code, never AI-written
    func = namespace[task["function"]]
    passes = sum(passes_episode(func, task, s) for s in range(EPISODES))
    assert passes == 0


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t["name"])
def test_reference_passes_every_audit_episode(task):
    namespace = {}
    exec(task["reference"], namespace)
    func = namespace[task["function"]]
    passes = sum(passes_episode(func, task, s) for s in range(EPISODES))
    assert passes == EPISODES