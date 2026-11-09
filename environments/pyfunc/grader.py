import json
import random
import re

from run_code_docker import run_python_sandboxed

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


def grade(reply, task, seed=0):
    """Return 1.0 only if every answer matches the expected answers."""
    code = extract_code(reply)
    if code is None:
        return 0.0
    inputs, expected = make_episode(task, seed)
    _ok, output = run_python_sandboxed(build_program(code, task, inputs), timeout=5)
    results = parse_results(output)
    if results is None or len(results) != len(expected):
        return 0.0
    for index, want in enumerate(expected):
        if results.get(index) != want:
            return 0.0
    return 1.0