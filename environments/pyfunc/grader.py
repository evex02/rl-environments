import json
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


def build_program(code, task):
    """Combine the AI's code (as plain text) with the question-asking harness."""
    inputs = [case[0] for case in task["cases"]]
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


def grade(reply, task):
    """Return 1.0 only if every answer matches the answer key, else 0.0."""
    code = extract_code(reply)
    if code is None:
        return 0.0
    _ok, output = run_python_sandboxed(build_program(code, task), timeout=5)
    results = parse_results(output)
    cases = task["cases"]
    if results is None or len(results) != len(cases):
        return 0.0
    for index, (_question, expected) in enumerate(cases):
        if results.get(index) != json.dumps(expected):
            return 0.0
    return 1.0