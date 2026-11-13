import pytest

from analyst_env import MAX_REPLIES, AnalystEnv
from analyst_tasks import TASKS, TOLERANCE, make_episode
from run_code_docker import docker_works

requires_docker = pytest.mark.skipif(not docker_works(), reason="Docker not available")

SENTINEL = 987654.32


def code_reply(code):
    return f"```python\n{code}\n```"


def sentinel_task():
    def make(rng):
        return {
            "csv": "x\n1\n2\n",
            "question": "What is x?",
            "answer": SENTINEL,
            "decoys": {"a": 1.0, "b": 2.0, "c": 3.0},
        }

    return {"name": "sentinel", "make": make}


# --- blind guessing (no Docker needed) ---

def best_blind_guess_rate(task, seeds):
    """The best a model could do by answering the same fixed number every time.
    The number is chosen with hindsight, so this overestimates a real guesser."""
    answers = [make_episode(task, s)["answer"] for s in seeds]
    best = 0
    for guess in set(answers):
        hits = sum(1 for a in answers if abs(a - guess) <= TOLERANCE + 1e-9)
        best = max(best, hits)
    return best / len(answers)


def test_the_blind_guess_measure_detects_a_task_with_a_constant_answer():
    constant = {
        "name": "constant",
        "make": lambda rng: {"csv": "", "question": "", "answer": 5.0, "decoys": {}},
    }
    assert best_blind_guess_rate(constant, range(50)) == 1.0


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t["name"])
def test_the_best_blind_guess_rarely_works(task):
    rate = best_blind_guess_rate(task, range(1500))
    print(f"\n{task['name']}: best blind guess scores {rate:.2%}")
    assert rate < 0.02


# --- reply-format cheats (no Docker needed) ---

def test_hedging_with_two_final_lines_scores_nothing():
    env = AnalystEnv(seed=0)
    env.reset()
    answer = env.episode["answer"]
    obs, reward, terminated, truncated, _info = env.step(
        f"FINAL: {answer}\nFINAL: {answer + 1}"
    )
    assert "more than one FINAL" in obs
    assert (reward, terminated, truncated) == (0.0, False, False)
    # The mistake cost a turn, but a clean answer is still accepted afterwards.
    _obs, reward, terminated, _truncated, info = env.step(f"FINAL: {answer}")
    assert (reward, terminated) == (1.0, True)
    assert info["turns"] == 2
    assert info["invalid_replies"] == 1


def test_odd_numbers_neither_score_nor_end_the_episode():
    for text in [
        "FINAL: nan",
        "FINAL: inf",
        "FINAL: -inf",
        "FINAL: 3 to 4",
        "FINAL: 1e3",
        "FINAL: 12.5%",
    ]:
        env = AnalystEnv(seed=0)
        env.reset()
        _obs, reward, terminated, truncated, info = env.step(text)
        assert (reward, terminated, truncated) == (0.0, False, False), text
        assert info["invalid_replies"] == 1, text


# --- tool-based cheats (these run the real sandbox) ---

@requires_docker
def test_final_text_printed_by_the_tool_is_never_an_answer():
    env = AnalystEnv(seed=0, tasks=[sentinel_task()])
    env.reset()
    for _ in range(MAX_REPLIES - 1):
        obs, reward, terminated, truncated, _info = env.step(
            code_reply(f"print('FINAL: {SENTINEL}')")
        )
        assert f"FINAL: {SENTINEL}" in obs  # the attack really ran
        assert (reward, terminated, truncated) == (0.0, False, False)
    _obs, reward, terminated, truncated, info = env.step(code_reply("print(1)"))
    assert (reward, terminated, truncated) == (0.0, False, True)
    assert info["reason"] == "no_final"
    assert info["tool_runs"] == MAX_REPLIES - 1

    # Control: the same text, sent as a reply instead, is accepted.
    control = AnalystEnv(seed=0, tasks=[sentinel_task()])
    control.reset()
    _obs, reward, terminated, _truncated, _info = control.step(f"FINAL: {SENTINEL}")
    assert (reward, terminated) == (1.0, True)


SCAN = (
    "import glob, os, sys\n"
    "needle = '9876' + '54'\n"
    "os.environ['CONTROL'] = needle\n"
    "hits = []\n"
    "if any(needle in k + v for k, v in os.environ.items()):\n"
    "    hits.append('environ')\n"
    "for path in glob.glob('/proc/[0-9]*/cmdline') + glob.glob('/proc/[0-9]*/environ'):\n"
    "    try:\n"
    "        if needle.encode() in open(path, 'rb').read():\n"
    "            hits.append(path)\n"
    "    except OSError:\n"
    "        pass\n"
    "for root, _dirs, files in os.walk('/tmp'):\n"
    "    for name in files:\n"
    "        try:\n"
    "            if needle in open(os.path.join(root, name), errors='ignore').read():\n"
    "                hits.append(name)\n"
    "        except OSError:\n"
    "            pass\n"
    "frame = sys._getframe()\n"
    "while frame is not None:\n"
    "    for key in ('DATA', 'CODE'):\n"
    "        if needle in str(frame.f_globals.get(key, '')):\n"
    "            hits.append('harness_' + key)\n"
    "    frame = frame.f_back\n"
    "print('HITS', hits)\n"
)


@requires_docker
def test_nothing_in_the_sandbox_contains_the_answer():
    env = AnalystEnv(seed=0, tasks=[sentinel_task()])
    env.reset()
    obs, *_ = env.step(code_reply(SCAN))
    # The one 'environ' hit is the planted control. Anything else would be a leak.
    assert "HITS ['environ']" in obs, obs


@requires_docker
def test_a_flooding_tool_is_reported_and_the_episode_can_continue():
    env = AnalystEnv(seed=0, tasks=[sentinel_task()])
    env.reset()
    flood = "import sys\nfor _ in range(2000):\n    sys.stdout.write('a' * 100000)\n"
    obs, reward, terminated, truncated, info = env.step(code_reply(flood))
    assert "too much output" in obs
    assert (reward, terminated, truncated) == (0.0, False, False)
    assert info["tool_errors"] == 1
    _obs, reward, terminated, _truncated, _info = env.step(f"FINAL: {SENTINEL}")
    assert (reward, terminated) == (1.0, True)