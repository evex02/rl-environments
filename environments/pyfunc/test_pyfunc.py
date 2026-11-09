import subprocess

import pytest

from grader import extract_code, grade
from tasks import TASKS


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

PALINDROME = TASKS[0]


def reply_with(code):
    return f"Here you go:\n```python\n{code}\n```"


# --- extract_code: no Docker needed ---

def test_extract_code_finds_python_block():
    assert extract_code(reply_with("x = 1")).strip() == "x = 1"


def test_extract_code_uses_last_block():
    reply = "```python\nfirst = 1\n```\nand then\n```python\nsecond = 2\n```"
    assert extract_code(reply).strip() == "second = 2"


def test_extract_code_returns_none_without_block():
    assert extract_code("just some words") is None


# --- grade: no Docker needed, because no code is run ---

def test_empty_reply_gets_zero():
    assert grade("", PALINDROME) == 0.0


def test_reply_without_code_block_gets_zero():
    assert grade("I think the answer is to reverse the text.", PALINDROME) == 0.0


# --- grade: these run code in the sandbox ---

@requires_docker
@pytest.mark.parametrize("task", TASKS, ids=lambda t: t["name"])
def test_reference_solution_gets_full_score(task):
    assert grade(reply_with(task["reference"]), task) == 1.0


@requires_docker
def test_wrong_solution_gets_zero():
    wrong = "def is_palindrome(text):\n    return text == text[::-1]"
    assert grade(reply_with(wrong), PALINDROME) == 0.0


@requires_docker
def test_syntax_error_gets_zero():
    broken = "def is_palindrome(text) return True"
    assert grade(reply_with(broken), PALINDROME) == 0.0


@requires_docker
def test_infinite_loop_gets_zero():
    assert grade(reply_with("while True: pass"), PALINDROME) == 0.0

# --- red team: cheats that must NOT earn a reward ---

CHEATS = {
    "exit_early": "import sys\nsys.exit(0)\n",
    "hard_exit": "import os\nos._exit(0)\n",
    "atexit_override": (
        "import atexit, os\n"
        "atexit.register(lambda: os._exit(0))\n"
        "def is_palindrome(text):\n"
        "    return False\n"
    ),
    "hardcode_examples": (
        "def is_palindrome(text):\n"
        "    answers = {'Racecar': True, 'hello': False}\n"
        "    return answers.get(text, False)\n"
    ),
    "forged_output": (
        "import os\n"
        "for i in range(8):\n"
        "    print('RESULT', i, 'true')\n"
        "os._exit(0)\n"
    ),
}


@requires_docker
@pytest.mark.parametrize("name", list(CHEATS))
def test_cheat_scores_zero(name):
    assert grade(reply_with(CHEATS[name]), PALINDROME) == 0.0