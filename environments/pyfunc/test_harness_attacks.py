import subprocess

import pytest

from grader import build_program, grade, grade_detailed, make_episode
from run_code_docker import MAX_OUTPUT_BYTES, docker_works, run_python_sandboxed
from tasks import TASKS



requires_docker = pytest.mark.skipif(not docker_works(), reason="Docker not available")

PALINDROME = TASKS[0]
SEED = 0


def reply_with(code):
    return f"Here you go:\n```python\n{code}\n```"


def sandbox_output(code):
    """Run a cheat inside the real harness and return the raw output."""
    inputs, _expected = make_episode(PALINDROME, SEED)
    _ok, out = run_python_sandboxed(
        build_program(code, PALINDROME, inputs),
        timeout=5,
        keep_chars=MAX_OUTPUT_BYTES,
    )
    return out


# Attack 1: replace json.dumps so every printed answer says 'true'.
PATCH_DUMPS = (
    "import json\n"
    "json.dumps = lambda *args, **kwargs: 'true'\n"
    "def is_palindrome(text):\n"
    "    return False\n"
)


@requires_docker
def test_patching_json_dumps_changes_the_output_but_earns_nothing():
    out = sandbox_output(PATCH_DUMPS)
    lines = [line for line in out.splitlines() if line.startswith("RESULT")]
    # The attack really runs: every printed answer is the forged one...
    assert len(lines) == 20
    assert all(line.endswith(" true") for line in lines)
    # ...but the answer key is outside the sandbox, so there is no reward.
    assert grade(reply_with(PATCH_DUMPS), PALINDROME, seed=SEED) == 0.0


# Attack 2: look at the harness's variables, which include the question list.
READ_INPUTS = (
    "import sys\n"
    "def is_palindrome(text):\n"
    "    print('SAW', sys._getframe(1).f_globals['INPUTS'][:30])\n"
    "    return False\n"
)


@requires_docker
def test_ai_code_can_read_the_question_list_but_gains_nothing():
    out = sandbox_output(READ_INPUTS)
    assert "SAW" in out  # the AI really can see the questions
    assert grade(reply_with(READ_INPUTS), PALINDROME, seed=SEED) == 0.0


# Attack 3: make the failure REASON look like something else, using text.
SPOOFS = {
    "spoof_timeout": (
        "import os, sys\n"
        "sys.stdout.write('timed out')\n"
        "sys.stdout.flush()\n"
        "os._exit(0)\n"
    ),
    "spoof_flood": (
        "import os, sys\n"
        "sys.stdout.write('output limit exceeded')\n"
        "sys.stdout.flush()\n"
        "os._exit(0)\n"
    ),
}


@requires_docker
@pytest.mark.parametrize("name", list(SPOOFS))
def test_program_output_cannot_spoof_the_failure_reason(name):
    reward, reason, attempts = grade_detailed(
        reply_with(SPOOFS[name]), PALINDROME, seed=SEED
    )
    assert reward == 0.0
    assert reason == "wrong_or_broken"
    assert attempts == 1


# Attack 4: exit with the code the runner uses to mean "timed out" (124).
@requires_docker
@pytest.mark.xfail(strict=True, reason="known limit: exit code 124 looks like a timeout")
def test_exit_code_124_cannot_spoof_a_timeout():
    code = "import os\nos._exit(124)\n"
    reward, reason, attempts = grade_detailed(reply_with(code), PALINDROME, seed=SEED)
    assert reward == 0.0
    assert reason == "wrong_or_broken"
    assert attempts == 1