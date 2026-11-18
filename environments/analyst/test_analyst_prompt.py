import pytest

from analyst_baseline import results_path
from analyst_env import (
    EXAMPLE_ANSWER,
    EXAMPLE_CODE,
    EXAMPLE_FINAL_LINE,
    AnalystEnv,
    build_prompt,
)
from analyst_parsing import parse_reply
from analyst_tasks import TASKS, make_episode


def an_episode():
    return make_episode(TASKS[0], 0)


def test_v1_is_the_default():
    episode = an_episode()
    assert build_prompt(episode) == build_prompt(episode, "v1")


def test_v2_only_adds_to_v1():
    episode = an_episode()
    v1, v2 = build_prompt(episode, "v1"), build_prompt(episode, "v2")
    assert v2.startswith(v1)
    assert len(v2) > len(v1)


def test_v1_has_no_example():
    v1 = build_prompt(an_episode(), "v1")
    assert "```" not in v1
    assert "FINAL: 777" not in v1


def test_v2_has_exactly_one_example_code_block():
    v2 = build_prompt(an_episode(), "v2")
    assert v2.count("```") == 2
    assert EXAMPLE_CODE in v2
    assert EXAMPLE_FINAL_LINE in v2


def test_v2_says_printed_text_is_never_an_answer():
    v2 = build_prompt(an_episode(), "v2")
    assert "never treated as an answer" in v2


def test_the_examples_are_valid_replies_under_the_parser():
    assert parse_reply(f"```python\n{EXAMPLE_CODE}\n```") == ("tool", EXAMPLE_CODE + "\n")
    assert parse_reply(EXAMPLE_FINAL_LINE) == ("final", EXAMPLE_ANSWER)


def test_the_example_answer_can_never_be_a_real_answer():
    # If this ever fails, pick a different example number.
    for task in TASKS:
        for seed in range(2000):
            answer = make_episode(task, seed)["answer"]
            assert abs(answer - EXAMPLE_ANSWER) > 1.0, (task["name"], seed)


def test_the_env_uses_v1_by_default_and_v2_on_request():
    a = AnalystEnv(seed=3)
    b = AnalystEnv(seed=3, prompt_version="v2")
    p1, p2 = a.reset(), b.reset()
    assert p2.startswith(p1)
    assert p2 != p1


def test_the_prompt_version_does_not_change_the_episodes():
    a = AnalystEnv(seed=3)
    b = AnalystEnv(seed=3, prompt_version="v2")
    for _ in range(5):
        a.reset()
        b.reset()
        assert a.episode == b.episode


def test_an_unknown_prompt_version_is_rejected():
    with pytest.raises(ValueError):
        AnalystEnv(prompt_version="v3")


def test_build_prompt_rejects_an_unknown_version():
    with pytest.raises(ValueError):
        build_prompt(an_episode(), "v3")


def test_each_prompt_version_has_its_own_results_file():
    assert results_path("v1").name == "analyst_baseline.json"
    assert results_path("v2").name == "analyst_baseline_prompt_v2.json"