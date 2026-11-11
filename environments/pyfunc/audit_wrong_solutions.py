import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for _folder in ("sandbox", "common"):
    sys.path.insert(0, str(ROOT / _folder))

from grader import make_episode
from tasks import TASKS

EPISODES = 200


def src(*lines):
    return "\n".join(lines) + "\n"


# Plausible WRONG solutions that we wrote ourselves. This script runs them
# directly on this computer, so it must only ever contain code we wrote.
# Never put AI-written code in here.
WRONG = {
    "is_palindrome": {
        "raw reversal": src(
            "def is_palindrome(text):",
            "    return text == text[::-1]",
        ),
        "case-sensitive": src(
            "def is_palindrome(text):",
            "    c = [x for x in text if x.isalnum()]",
            "    return c == c[::-1]",
        ),
        "keeps punctuation": src(
            "def is_palindrome(text):",
            "    t = text.lower()",
            "    return t == t[::-1]",
        ),
        "drops digits": src(
            "def is_palindrome(text):",
            "    c = [x.lower() for x in text if x.isalpha()]",
            "    return c == c[::-1]",
        ),
    },
    "second_largest": {
        "returns the largest": src(
            "def second_largest(numbers):",
            "    return max(numbers) if numbers else None",
        ),
        "ignores 'distinct'": src(
            "def second_largest(numbers):",
            "    s = sorted(numbers, reverse=True)",
            "    return s[1] if len(s) >= 2 else None",
        ),
        "second smallest": src(
            "def second_largest(numbers):",
            "    s = sorted(set(numbers))",
            "    return s[1] if len(s) >= 2 else None",
        ),
        "crashes on short input": src(
            "def second_largest(numbers):",
            "    return sorted(set(numbers))[-2]",
        ),
    },
    "run_length_encode": {
        "drops counts of 1": src(
            "def run_length_encode(text):",
            "    out, i = [], 0",
            "    while i < len(text):",
            "        j = i",
            "        while j < len(text) and text[j] == text[i]:",
            "            j += 1",
            "        out.append(text[i] + (str(j - i) if j - i > 1 else ''))",
            "        i = j",
            "    return ''.join(out)",
        ),
        "counts letters overall": src(
            "def run_length_encode(text):",
            "    seen = []",
            "    for c in text:",
            "        if c not in seen:",
            "            seen.append(c)",
            "    return ''.join(c + str(text.count(c)) for c in seen)",
        ),
        "forgets the last run": src(
            "def run_length_encode(text):",
            "    if not text:",
            "        return ''",
            "    out, count = '', 1",
            "    for i in range(1, len(text)):",
            "        if text[i] == text[i - 1]:",
            "            count += 1",
            "        else:",
            "            out += text[i - 1] + str(count)",
            "            count = 1",
            "    return out",
        ),
    },
    "fizzbuzz_list": {
        "checks 3 before 15": src(
            "def fizzbuzz_list(n):",
            "    out = []",
            "    for i in range(1, n + 1):",
            "        if i % 3 == 0:",
            "            out.append('Fizz')",
            "        elif i % 5 == 0:",
            "            out.append('Buzz')",
            "        else:",
            "            out.append(str(i))",
            "    return out",
        ),
        "excludes n": src(
            "def fizzbuzz_list(n):",
            "    out = []",
            "    for i in range(1, n):",
            "        if i % 15 == 0:",
            "            out.append('FizzBuzz')",
            "        elif i % 3 == 0:",
            "            out.append('Fizz')",
            "        elif i % 5 == 0:",
            "            out.append('Buzz')",
            "        else:",
            "            out.append(str(i))",
            "    return out",
        ),
        "numbers not strings": src(
            "def fizzbuzz_list(n):",
            "    out = []",
            "    for i in range(1, n + 1):",
            "        if i % 15 == 0:",
            "            out.append('FizzBuzz')",
            "        elif i % 3 == 0:",
            "            out.append('Fizz')",
            "        elif i % 5 == 0:",
            "            out.append('Buzz')",
            "        else:",
            "            out.append(i)",
            "    return out",
        ),
    },
    "merge_intervals": {
        "touching not merged": src(
            "def merge_intervals(intervals):",
            "    merged = []",
            "    for start, end in sorted(intervals):",
            "        if merged and start < merged[-1][1]:",
            "            merged[-1][1] = max(merged[-1][1], end)",
            "        else:",
            "            merged.append([start, end])",
            "    return merged",
        ),
        "forgets to sort": src(
            "def merge_intervals(intervals):",
            "    merged = []",
            "    for start, end in intervals:",
            "        if merged and start <= merged[-1][1]:",
            "            merged[-1][1] = max(merged[-1][1], end)",
            "        else:",
            "            merged.append([start, end])",
            "    return merged",
        ),
        "keeps the last end, not the larger": src(
            "def merge_intervals(intervals):",
            "    merged = []",
            "    for start, end in sorted(intervals):",
            "        if merged and start <= merged[-1][1]:",
            "            merged[-1][1] = end",
            "        else:",
            "            merged.append([start, end])",
            "    return merged",
        ),
    },
}


def passes_episode(func, task, seed):
    """True if this function answers every question of the episode correctly."""
    inputs, expected = make_episode(task, seed)
    for arg, want in zip(inputs, expected):
        try:
            got = json.dumps(func(copy.deepcopy(arg)))
        except Exception:
            return False
        if got != want:
            return False
    return True


def main():
    print("Episodes where the solution earns reward 1.0 (out of", EPISODES, ")\n")
    for task in TASKS:
        candidates = {"REFERENCE (should be all)": task["reference"]}
        candidates.update(WRONG[task["name"]])
        for label, code in candidates.items():
            namespace = {}
            exec(code, namespace)
            func = namespace[task["function"]]
            passes = sum(passes_episode(func, task, s) for s in range(EPISODES))
            print(f"{task['name']:18s} {label:36s} {passes:3d}/{EPISODES}")
        print()


if __name__ == "__main__":
    main()