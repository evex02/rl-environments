import re
import pytest
from addition_env import AdditionEnv


def test_reset_gives_a_question():
    env = AdditionEnv(seed=1)
    question = env.reset()
    assert "What is" in question


def test_correct_reply_gets_full_score():
    env = AdditionEnv(seed=1)
    env.reset()
    assert env.step(f"Answer: {env.correct}") == 1.0


def test_wrong_reply_gets_zero():
    env = AdditionEnv(seed=1)
    env.reset()
    assert env.step(f"Answer: {env.correct + 1}") == 0.0


def test_same_seed_gives_same_question():
    assert AdditionEnv(seed=7).reset() == AdditionEnv(seed=7).reset()


def test_cannot_answer_twice_in_one_episode():
    env = AdditionEnv(seed=1)
    env.reset()
    env.step("Answer: 0")
    with pytest.raises(RuntimeError):
        env.step(f"Answer: {env.correct}")


def test_cannot_answer_before_reset():
    env = AdditionEnv(seed=1)
    with pytest.raises(RuntimeError):
        env.step("Answer: 4")

def test_digits_controls_size_of_numbers():
    env = AdditionEnv(seed=1, digits=4)
    question = env.reset()
    numbers = re.findall(r"\d+", question)[:2]
    assert all(len(n) == 4 for n in numbers)