import subprocess

import pytest

from pyfunc_env import PyFuncEnv


def docker_works():
    try:
        result = subprocess.run(
            ["wsl", "-u", "root", "--", "docker", "info"],
            capture_output=True,
            timeout=30,
        )
        return result.returncode == 0
    except Exception:
        return False


requires_docker = pytest.mark.skipif(not docker_works(), reason="Docker not available")


def test_reset_returns_the_prompt():
    env = PyFuncEnv(seed=0)
    prompt = env.reset()
    assert "is_palindrome" in prompt


def test_step_before_reset_raises():
    env = PyFuncEnv(seed=0)
    with pytest.raises(RuntimeError):
        env.step("anything")


def test_cannot_step_twice_in_one_episode():
    env = PyFuncEnv(seed=0)
    env.reset()
    env.step("no code here")
    with pytest.raises(RuntimeError):
        env.step("no code here")


def test_same_seed_gives_same_episodes():
    a, b = PyFuncEnv(seed=5), PyFuncEnv(seed=5)
    seeds_a, seeds_b = [], []
    for _ in range(5):
        a.reset()
        b.reset()
        seeds_a.append(a.episode_seed)
        seeds_b.append(b.episode_seed)
    assert seeds_a == seeds_b


def test_episode_seeds_change_between_resets():
    env = PyFuncEnv(seed=0)
    seeds = []
    for _ in range(5):
        env.reset()
        seeds.append(env.episode_seed)
    assert len(set(seeds)) == 5


def test_reply_without_code_scores_zero():
    env = PyFuncEnv(seed=0)
    env.reset()
    assert env.step("I would reverse the string.") == 0.0


@requires_docker
def test_reference_solution_scores_full_marks_through_env():
    env = PyFuncEnv(seed=1)
    env.reset()
    reply = f"```python\n{env.task['reference']}\n```"
    assert env.step(reply) == 1.0