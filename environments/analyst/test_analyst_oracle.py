import re

import pytest

from analyst_env import AnalystEnv
from analyst_tasks import TASKS
from run_code_docker import docker_works

pytestmark = pytest.mark.skipif(not docker_works(), reason="Docker not available")

SEEDS = range(6)


def code_reply(code):
    return f"```python\n{code}\n```"


def oracle_code(task_name, prompt):
    """Python that a perfect solver would write. Written separately from the
    generators: it only reads the CSV file and calculates the answer."""
    if task_name == "mean_clean":
        return (
            "import csv\n"
            "rows = list(csv.DictReader(open('/tmp/data.csv')))\n"
            "vals = [float(r['reading']) for r in rows]\n"
            "valid = [v for v in vals if v != -999]\n"
            "print(round(sum(valid) / len(valid), 2))\n"
        )
    if task_name == "group_median":
        target = re.search(r"for the group `(\w+)`", prompt).group(1)
        return (
            "import csv, statistics\n"
            "rows = list(csv.DictReader(open('/tmp/data.csv')))\n"
            f"vals = [float(r['value']) for r in rows if r['group'] == {target!r}]\n"
            "print(round(statistics.median(vals), 2))\n"
        )
    if task_name == "pct_change":
        first, second = re.findall(r"`(\d{4}-\d{2})`", prompt)
        return (
            "import csv\n"
            "rows = list(csv.DictReader(open('/tmp/data.csv')))\n"
            "totals = {}\n"
            "for r in rows:\n"
            "    totals[r['month']] = totals.get(r['month'], 0.0) + float(r['amount'])\n"
            f"t1, t2 = totals[{first!r}], totals[{second!r}]\n"
            "print(round((t2 - t1) / t1 * 100, 2))\n"
        )
    raise ValueError(task_name)


def run_oracle(task, seed, offset=0.0):
    """Play a full episode through the real sandbox: one tool call, then FINAL."""
    env = AnalystEnv(seed=seed, tasks=[task])
    prompt = env.reset()
    code = oracle_code(task["name"], prompt)
    obs, _reward, _terminated, _truncated, info = env.step(code_reply(code))
    assert info["tool_errors"] == 0, obs
    match = re.search(r"TOOL OUTPUT:\n(\S+)", obs)
    assert match, obs
    number = float(match.group(1)) + offset
    return env.step(f"FINAL: {number:.6f}")


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t["name"])
def test_the_oracle_scores_full_marks(task):
    for seed in SEEDS:
        _obs, reward, terminated, truncated, info = run_oracle(task, seed)
        assert (reward, terminated, truncated) == (1.0, True, False), seed
        assert info == {
            "reason": "pass",
            "turns": 2,
            "tool_runs": 1,
            "tool_errors": 0,
            "invalid_replies": 0,
        }


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t["name"])
def test_a_slightly_wrong_number_from_the_oracle_scores_zero(task):
    for offset in (0.5, 0.02):
        _obs, reward, terminated, _truncated, info = run_oracle(task, 0, offset)
        assert (reward, terminated) == (0.0, True), offset
        assert info["reason"] == "wrong_answer"


def test_each_tool_run_starts_fresh_and_the_data_is_restored():
    env = AnalystEnv(seed=0, tasks=[TASKS[0]])
    env.reset()
    header = env.episode["csv"].splitlines()[0]
    env.step(
        code_reply(
            "open('/tmp/marker', 'w').write('x')\n"
            "open('/tmp/data.csv', 'w').write('tampered')\n"
            "print('done')"
        )
    )
    obs, *_ = env.step(
        code_reply(
            "import os\n"
            "print(os.path.exists('/tmp/marker'))\n"
            "print(open('/tmp/data.csv').readline().strip())"
        )
    )
    assert "False" in obs
    assert header in obs
    assert "tampered" not in obs


def test_a_crashing_program_is_reported_to_the_model():
    env = AnalystEnv(seed=0, tasks=[TASKS[0]])
    env.reset()
    obs, _reward, terminated, truncated, info = env.step(code_reply("print(1 / 0)"))
    assert "ZeroDivisionError" in obs
    assert (terminated, truncated) == (False, False)
    assert info["tool_errors"] == 1


def test_an_infinite_loop_is_reported_to_the_model():
    env = AnalystEnv(seed=0, tasks=[TASKS[0]])
    env.reset()
    obs, _reward, _terminated, _truncated, info = env.step(code_reply("while True: pass"))
    assert "ran out of time" in obs
    assert info["tool_errors"] == 1