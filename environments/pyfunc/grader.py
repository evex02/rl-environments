import json
import random
import re

from run_code_docker import MAX_OUTPUT_BYTES, run_python_detailed

CODE_BLOCK = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)
RESULT_LINE = re.compile(r"RESULT (\d+) (.*)")

# This text runs INSIDE the sandbox. It loads the AI's code, asks the
# function each question, and prints the answers. It never sees the
# expected answers.
HARNESS = r'''
import json, sys

_ns = {}
exec(SOLUTION, _ns)
_func = _ns[FUNC]
for _i, _arg in enumerate(json.loads(INPUTS)):
    _result = _func(_arg)
    sys.stdout.write("\nRESULT %d %s\n" % (_i, json.dumps(_result)))
    sys.stdout.flush()
'''


def extract_code(reply):
    """Return the code from the last Markdown code block, or None."""
    blocks = CODE_BLOCK.findall(reply)
    if not blocks:
        return None
    return blocks[-1]


def make_episode(task, seed):
    """Build one episode: fresh inputs, plus the expected answers.

    The expected answers come from OUR reference solution, run here on the
    host. That is safe only because we wrote it. AI code never runs here.
    """
    inputs = task["generate"](random.Random(seed))
    namespace = {}
    exec(task["reference"], namespace)
    reference = namespace[task["function"]]
    expected = [json.dumps(reference(x)) for x in inputs]
    return inputs, expected


def build_program(code, task, inputs):
    """Combine the AI's code (as plain text) with the question-asking harness."""
    header = (
        f"SOLUTION = {code!r}\n"
        f"FUNC = {task['function']!r}\n"
        f"INPUTS = {json.dumps(inputs)!r}\n"
    )
    return header + HARNESS


def parse_results(output):
    """Collect 'RESULT <number> <answer>' lines. Return None on duplicates."""
    results = {}
    for line in output.splitlines():
        match = RESULT_LINE.fullmatch(line)
        if match:
            index = int(match.group(1))
            if index in results:
                return None  # the same question answered twice: suspicious
            results[index] = match.group(2)
    return results


MAX_ATTEMPTS = 2  # one retry, and only for timeouts


def grade_detailed(reply, task, seed=0):
    """Return (reward, reason, attempts).

    reason is one of: pass, no_code, wrong_or_broken, timeout, flood.
    The reason comes from the runner's status, never from the program's
    output. Only a timeout is retried: a stall on the machine can look like
    an infinite loop, but a retry never forgives a wrong answer.
    """
    code = extract_code(reply)
    if code is None:
        return 0.0, "no_code", 0
    inputs, expected = make_episode(task, seed)
    program = build_program(code, task, inputs)

    attempts = 0
    while True:
        attempts += 1
        status, output = run_python_detailed(
            program, timeout=5, keep_chars=MAX_OUTPUT_BYTES
        )
        if status == "timeout" and attempts < MAX_ATTEMPTS:
            continue
        break

    if status == "timeout":
        return 0.0, "timeout", attempts
    if status == "flood":
        return 0.0, "flood", attempts
    results = parse_results(output)
    if results is None or len(results) != len(expected):
        return 0.0, "wrong_or_broken", attempts
    for index, want in enumerate(expected):
        if results.get(index) != want:
            return 0.0, "wrong_or_broken", attempts
    return 1.0, "pass", attempts


def grade(reply, task, seed=0):
    """Just the reward. Everything else in the project can keep using this."""
    return grade_detailed(reply, task, seed)[0]