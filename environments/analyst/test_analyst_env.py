import pytest

from analyst_env import MAX_REPLIES, AnalystEnv
from analyst_tasks import TASKS, TOLERANCE


def code_reply(code="print(1)"):
    return f"```python\n{code}\n```"


class FakeTool:
    """A pretend sandbox: returns the given (status, output) pairs in order."""

    def __init__(self, results=None):
        self.results = results or [("ok", "42\n")]
        self.programs = []
        self.settings = []

    def __call__(self, program, timeout=5, keep_chars=2000):
        self.programs.append(program)
        self.settings.append((timeout, keep_chars))
        return self.results[min(len(self.programs), len(self.results)) - 1]


def new_env(tool=None, seed=0, tasks=None):
    tool = tool or FakeTool()
    return AnalystEnv(seed=seed, tasks=tasks, run_tool=tool), tool


def sentinel_task():
    def make(rng):
        return {
            "csv": "x\n1\n2\n",
            "question": "What is x?",
            "answer": 987654.32,
            "decoys": {"a": 1.0, "b": 2.0, "c": 3.0},
        }

    return {"name": "sentinel", "make": make}


# --- starting an episode ---

def test_reset_describes_the_task():
    env, _ = new_env()
    prompt = env.reset()
    assert env.episode["question"] in prompt
    assert "/tmp/data.csv" in prompt
    assert "FINAL:" in prompt
    assert f"{MAX_REPLIES} replies in total" in prompt
    header = env.episode["csv"].splitlines()[0]
    assert header in prompt


def test_reset_does_not_reveal_the_data():
    env, _ = new_env()
    prompt = env.reset()
    assert env.episode["csv"] not in prompt


def test_step_before_reset_raises():
    env, _ = new_env()
    with pytest.raises(RuntimeError):
        env.step("FINAL: 1")


def test_step_after_the_episode_ended_raises():
    env, _ = new_env()
    env.reset()
    env.step("FINAL: 1")
    with pytest.raises(RuntimeError):
        env.step("FINAL: 1")


def test_same_seed_gives_the_same_episodes():
    a, _ = new_env(seed=7)
    b, _ = new_env(seed=7)
    for _ in range(5):
        assert a.reset() == b.reset()
        assert a.episode["answer"] == b.episode["answer"]


def test_every_task_is_used():
    env, _ = new_env()
    names = set()
    for _ in range(30):
        env.reset()
        names.add(env.task["name"])
    assert names == {t["name"] for t in TASKS}


# --- final answers ---

def test_a_correct_final_answer_scores_one():
    env, _ = new_env()
    env.reset()
    answer = env.episode["answer"]
    _obs, reward, terminated, truncated, info = env.step(f"FINAL: {answer}")
    assert (reward, terminated, truncated) == (1.0, True, False)
    assert info["reason"] == "pass"


def test_a_wrong_final_answer_scores_zero():
    env, _ = new_env()
    env.reset()
    answer = env.episode["answer"]
    _obs, reward, terminated, truncated, info = env.step(f"FINAL: {answer + 1}")
    assert (reward, terminated, truncated) == (0.0, True, False)
    assert info["reason"] == "wrong_answer"


@pytest.mark.parametrize(
    "offset,expected",
    [
        (0.0, 1.0),
        (0.005, 1.0),
        (TOLERANCE, 1.0),
        (-TOLERANCE, 1.0),
        (0.02, 0.0),
        (-0.02, 0.0),
    ],
)
def test_the_tolerance_boundary(offset, expected):
    env, _ = new_env()
    env.reset()
    value = env.episode["answer"] + offset
    _obs, reward, _terminated, _truncated, _info = env.step(f"FINAL: {value:.6f}")
    assert reward == expected


# --- tool calls ---

def test_a_code_reply_runs_the_tool_and_shows_its_output():
    env, tool = new_env(FakeTool([("ok", "42\n")]))
    env.reset()
    obs, reward, terminated, truncated, info = env.step(code_reply("print(42)"))
    assert len(tool.programs) == 1
    assert "42" in obs
    assert (reward, terminated, truncated) == (0.0, False, False)
    assert info["tool_runs"] == 1


def test_the_model_is_told_how_many_replies_are_left():
    env, _ = new_env()
    env.reset()
    obs, *_ = env.step("hmm")
    assert "You have 4 replies left." in obs
    for _ in range(2):
        obs, *_ = env.step("hmm")
    obs, *_ = env.step("hmm")
    assert "You have 1 reply left." in obs


def test_the_program_sent_to_the_tool_has_the_data_and_the_code():
    env, tool = new_env()
    env.reset()
    env.step(code_reply("print('marker_xyz')"))
    program = tool.programs[0]
    assert "marker_xyz" in program
    assert repr(env.episode["csv"]) in program
    assert "/tmp/data.csv" in program


def test_the_tool_gets_the_documented_limits():
    env, tool = new_env()
    env.reset()
    env.step(code_reply())
    assert tool.settings == [(5, 2000)]


def test_the_true_answer_never_reaches_the_tool_or_the_model():
    env, tool = new_env(tasks=[sentinel_task()])
    prompt = env.reset()
    obs, *_ = env.step(code_reply("print(1)"))
    assert "987654" not in prompt
    assert "987654" not in tool.programs[0]
    assert "987654" not in obs


# --- invalid replies ---

@pytest.mark.parametrize(
    "reply,fragment",
    [
        ("I think it is about 5.", "neither"),
        (code_reply("print(1)") + "\n" + code_reply("print(2)"), "more than one code block"),
        ("FINAL: 1\nFINAL: 2", "more than one FINAL"),
        ("FINAL: about 5", "plain number"),
    ],
)
def test_invalid_replies_are_explained_and_run_nothing(reply, fragment):
    env, tool = new_env()
    env.reset()
    obs, reward, terminated, truncated, info = env.step(reply)
    assert fragment in obs
    assert tool.programs == []
    assert (reward, terminated, truncated) == (0.0, False, False)
    assert info["invalid_replies"] == 1


# --- running out of replies ---

def test_using_every_reply_without_a_final_answer_truncates():
    env, _ = new_env()
    env.reset()
    for _ in range(MAX_REPLIES - 1):
        _obs, _reward, terminated, truncated, _info = env.step("no idea")
        assert (terminated, truncated) == (False, False)
    _obs, reward, terminated, truncated, info = env.step("no idea")
    assert (reward, terminated, truncated) == (0.0, False, True)
    assert info["reason"] == "no_final"
    assert info["turns"] == MAX_REPLIES


def test_a_code_reply_on_the_last_turn_is_not_run():
    env, tool = new_env()
    env.reset()
    for _ in range(MAX_REPLIES - 1):
        env.step("no idea")
    _obs, reward, terminated, truncated, _info = env.step(code_reply())
    assert (reward, terminated, truncated) == (0.0, False, True)
    assert tool.programs == []


def test_a_valid_final_answer_on_the_last_turn_still_counts():
    env, _ = new_env()
    env.reset()
    for _ in range(MAX_REPLIES - 1):
        env.step("no idea")
    answer = env.episode["answer"]
    _obs, reward, terminated, truncated, info = env.step(f"FINAL: {answer}")
    assert (reward, terminated, truncated) == (1.0, True, False)
    assert info["reason"] == "pass"


# --- what the model is told about tool results ---

@pytest.mark.parametrize(
    "status,output,fragment,counts_as_error",
    [
        ("ok", "", "(no output)", False),
        ("error", "Traceback (most recent call last):\nValueError: boom", "ValueError: boom", True),
        ("timeout", "", "ran out of time", True),
        ("flood", "", "too much output", True),
    ],
)
def test_tool_results_are_reported_to_the_model(status, output, fragment, counts_as_error):
    env, _ = new_env(FakeTool([(status, output)]))
    env.reset()
    obs, _reward, _terminated, _truncated, info = env.step(code_reply())
    assert fragment in obs
    assert info["tool_errors"] == (1 if counts_as_error else 0)


# --- cheats ---

def test_final_text_printed_by_the_tool_is_not_an_answer():
    env, _ = new_env(FakeTool([("ok", "FINAL: 1.0\n")]))
    env.reset()
    _obs, reward, terminated, truncated, _info = env.step(code_reply())
    assert (reward, terminated, truncated) == (0.0, False, False)


def test_code_in_a_reply_with_a_final_line_is_not_run():
    env, tool = new_env()
    env.reset()
    env.step(code_reply() + "\nFINAL: 1")
    assert tool.programs == []


# --- bookkeeping ---

def test_info_reports_what_happened():
    env, _ = new_env()
    env.reset()
    env.step("hmm")
    env.step(code_reply())
    env.step(code_reply())
    answer = env.episode["answer"]
    _obs, _reward, _terminated, _truncated, info = env.step(f"FINAL: {answer}")
    assert info == {
        "reason": "pass",
        "turns": 4,
        "tool_runs": 2,
        "tool_errors": 0,
        "invalid_replies": 1,
    }