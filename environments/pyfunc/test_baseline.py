from baseline import summarise


def rec(task, reward, has_code=True):
    return {"task": task, "reward": reward, "has_code": has_code}


def test_summarise_counts_passes_per_task():
    s = summarise([rec("a", 1.0), rec("a", 0.0), rec("b", 0.0)])
    assert s["a"]["n"] == 2
    assert s["a"]["pass_rate"] == 0.5
    assert s["b"]["pass_rate"] == 0.0


def test_summarise_has_an_overall_row():
    s = summarise([rec("a", 1.0), rec("b", 0.0)])
    assert s["ALL"]["n"] == 2
    assert s["ALL"]["pass_rate"] == 0.5


def test_summarise_tracks_missing_code_blocks():
    s = summarise([rec("a", 0.0, has_code=False), rec("a", 1.0)])
    assert s["a"]["code_block_rate"] == 0.5


def test_interval_contains_the_rate():
    s = summarise([rec("a", 1.0)] * 3 + [rec("a", 0.0)] * 7)
    assert s["a"]["low"] <= 0.3 <= s["a"]["high"]