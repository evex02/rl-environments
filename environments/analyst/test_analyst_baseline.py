from analyst_baseline import summarise


def rec(task, reward, reason, turns=2, tool_errors=0, invalid=0):
    return {
        "task": task,
        "reward": reward,
        "reason": reason,
        "turns": turns,
        "tool_runs": max(turns - 1, 0),
        "tool_errors": tool_errors,
        "invalid_replies": invalid,
    }


def test_pass_rate_per_task_and_overall():
    s = summarise(
        [rec("a", 1.0, "pass"), rec("a", 0.0, "wrong_answer"), rec("b", 0.0, "no_final", 5)]
    )
    assert s["a"]["n"] == 2
    assert s["a"]["pass_rate"] == 0.5
    assert s["b"]["pass_rate"] == 0.0
    assert s["ALL"]["n"] == 3


def test_reasons_are_counted():
    s = summarise(
        [rec("a", 1.0, "pass"), rec("a", 0.0, "no_final", 5), rec("a", 0.0, "no_final", 5)]
    )
    assert s["a"]["reasons"] == {"pass": 1, "no_final": 2}


def test_average_turns():
    s = summarise([rec("a", 1.0, "pass", 2), rec("a", 0.0, "no_final", 4)])
    assert s["a"]["mean_turns"] == 3.0


def test_tool_error_and_invalid_reply_rates():
    s = summarise(
        [rec("a", 0.0, "no_final", 5, tool_errors=2, invalid=1), rec("a", 1.0, "pass", 2)]
    )
    assert s["a"]["tool_error_rate"] == 0.4  # 2 errors in 5 tool runs
    assert s["a"]["invalid_per_episode"] == 0.5


def test_interval_contains_the_rate():
    s = summarise([rec("a", 1.0, "pass")] * 3 + [rec("a", 0.0, "wrong_answer")] * 7)
    assert s["a"]["low"] <= 0.3 <= s["a"]["high"]

def test_retries_and_cut_offs_are_totalled():
    rows = [
        {**rec("a", 0.0, "no_final", 5), "retries": 1, "cut_offs": 2},
        {**rec("a", 1.0, "pass", 2), "retries": 0, "cut_offs": 0},
    ]
    s = summarise(rows)
    assert s["a"]["retries"] == 1
    assert s["a"]["cut_offs"] == 2