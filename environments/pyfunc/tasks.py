REPLY_RULE = (
    "Reply with a single Markdown code block marked python that "
    "defines the function."
)


LETTERS = "abcde"
DIGITS = "123"
PUNCT = " ,.!?"


def _mirror(rng, alphabet, lo=2, hi=5):
    """An exact palindrome made only from the given characters."""
    half = "".join(rng.choice(alphabet) for _ in range(rng.randint(lo, hi)))
    return half + rng.choice(["", rng.choice(alphabet)]) + half[::-1]


def _disguise(rng, text):
    """Random upper/lower case and extra punctuation. A palindrome stays one."""
    out = []
    for ch in text:
        if rng.random() < 0.3:
            out.append(rng.choice(PUNCT))
        out.append(ch.upper() if rng.random() < 0.5 else ch.lower())
    return "".join(out)


def _case_trap(rng):
    """True, but only if case is ignored: 'Abcba' style."""
    p = _mirror(rng, LETTERS)
    return p[0].upper() + p[1:-1] + p[-1].lower()


def _punctuation_trap(rng):
    """True, but only if punctuation is ignored: '!abcba' style."""
    return rng.choice("!?.,") + _mirror(rng, LETTERS)


def _digit_trap(rng):
    """False, but only if digits are counted: 'a1bb2a' style."""
    p = _mirror(rng, LETTERS)
    d1, d2 = rng.sample(DIGITS, 2)
    return p[0] + d1 + p[1:-1] + d2 + p[-1]


def _near_miss(rng):
    """A palindrome with one character changed (usually no longer one)."""
    p = list(_mirror(rng, LETTERS + DIGITS))
    i = rng.randrange(len(p))
    p[i] = rng.choice([c for c in LETTERS + DIGITS if c != p[i]])
    return "".join(p)


def _palindrome_inputs(rng, n=20):
    """Fresh inputs per episode. Every rule in the prompt is tested by at
    least one input in EVERY episode, not left to chance."""
    inputs = [
        "",
        "a",
        _case_trap(rng),
        _punctuation_trap(rng),
        _digit_trap(rng),
        _near_miss(rng),
    ]
    while len(inputs) < n:
        kind = rng.random()
        if kind < 0.4:
            inputs.append(_disguise(rng, _mirror(rng, LETTERS + DIGITS)))
        elif kind < 0.7:
            inputs.append(_near_miss(rng))
        else:
            inputs.append(
                "".join(
                    rng.choice(LETTERS + DIGITS + PUNCT)
                    for _ in range(rng.randint(2, 10))
                )
            )
    rng.shuffle(inputs)
    return inputs


def _second_largest_inputs(rng, n=20):
    inputs = [[], [4], [2, 2], [1, 2]]
    while len(inputs) < n:
        size = rng.randint(2, 8)
        inputs.append([rng.randint(-5, 10) for _ in range(size)])
    return inputs


def _rle_inputs(rng, n=20):
    letters = "abcxyz"
    inputs = ["", "a"]
    while len(inputs) < n:
        text, last = "", None
        for _ in range(rng.randint(1, 5)):
            last = rng.choice([c for c in letters if c != last])
            text += last * rng.randint(1, 4)
        inputs.append(text)
    return inputs


def _fizzbuzz_inputs(rng, n=20):
    inputs = [0, 1, 15]
    while len(inputs) < n:
        inputs.append(rng.randint(5, 40))
    return inputs


def _nested_intervals(rng):
    """An outer interval, a smaller one inside it, and a separate one."""
    start = rng.randint(0, 10)
    outer = [start, start + rng.randint(6, 10)]
    inner = [start + 1, start + rng.randint(2, 4)]
    far = [start + 30, start + 31]
    pairs = [outer, inner, far]
    rng.shuffle(pairs)
    return pairs


def _intervals_inputs(rng, n=20):
    inputs = [[], [[1, 3]], _nested_intervals(rng)]
    while len(inputs) < n:
        pairs = []
        for _ in range(rng.randint(2, 6)):
            start = rng.randint(0, 20)
            pairs.append([start, start + rng.randint(0, 5)])
        inputs.append(pairs)
    return inputs


TASKS = [
    {
        "name": "is_palindrome",
        "function": "is_palindrome",
        "prompt": (
            "Write a Python function `is_palindrome(text)` that returns True "
            "if `text` reads the same forwards and backwards, ignoring "
            "upper/lower case and any character that is not a letter or "
            "digit, and False otherwise.\n\n"
            "Examples:\n"
            "is_palindrome('Racecar') -> True\n"
            "is_palindrome('A man, a plan, a canal: Panama') -> True\n"
            "is_palindrome('hello') -> False\n\n" + REPLY_RULE
        ),
        "generate": _palindrome_inputs,
        "reference": (
            "def is_palindrome(text):\n"
            "    cleaned = [c.lower() for c in text if c.isalnum()]\n"
            "    return cleaned == cleaned[::-1]\n"
        ),
    },
    {
        "name": "second_largest",
        "function": "second_largest",
        "prompt": (
            "Write a Python function `second_largest(numbers)` that takes a "
            "list of integers and returns the second largest DISTINCT value. "
            "If the list has fewer than two distinct values, return None.\n\n"
            "Examples:\n"
            "second_largest([3, 1, 2]) -> 2\n"
            "second_largest([5, 5, 4]) -> 4\n"
            "second_largest([7]) -> None\n\n" + REPLY_RULE
        ),
        "generate": _second_largest_inputs,
        "reference": (
            "def second_largest(numbers):\n"
            "    values = sorted(set(numbers), reverse=True)\n"
            "    return values[1] if len(values) >= 2 else None\n"
        ),
    },
    {
        "name": "run_length_encode",
        "function": "run_length_encode",
        "prompt": (
            "Write a Python function `run_length_encode(text)` that "
            "compresses a string of letters by replacing each run of "
            "identical consecutive characters with that character followed "
            "by the length of the run. The input contains only letters. "
            "Return an empty string for an empty input.\n\n"
            "Examples:\n"
            "run_length_encode('aaabcc') -> 'a3b1c2'\n"
            "run_length_encode('z') -> 'z1'\n"
            "run_length_encode('') -> ''\n\n" + REPLY_RULE
        ),
        "generate": _rle_inputs,
        "reference": (
            "def run_length_encode(text):\n"
            "    out = []\n"
            "    i = 0\n"
            "    while i < len(text):\n"
            "        j = i\n"
            "        while j < len(text) and text[j] == text[i]:\n"
            "            j += 1\n"
            "        out.append(text[i] + str(j - i))\n"
            "        i = j\n"
            "    return ''.join(out)\n"
        ),
    },
    {
        "name": "fizzbuzz_list",
        "function": "fizzbuzz_list",
        "prompt": (
            "Write a Python function `fizzbuzz_list(n)` that returns a list "
            "of strings for the numbers 1 to n inclusive. For a multiple of "
            "both 3 and 5 use 'FizzBuzz', for a multiple of 3 use 'Fizz', "
            "for a multiple of 5 use 'Buzz', otherwise use the number as a "
            "string. If n is less than 1, return an empty list.\n\n"
            "Examples:\n"
            "fizzbuzz_list(3) -> ['1', '2', 'Fizz']\n"
            "fizzbuzz_list(5) -> ['1', '2', 'Fizz', '4', 'Buzz']\n"
            "fizzbuzz_list(0) -> []\n\n" + REPLY_RULE
        ),
        "generate": _fizzbuzz_inputs,
        "reference": (
            "def fizzbuzz_list(n):\n"
            "    out = []\n"
            "    for i in range(1, n + 1):\n"
            "        if i % 15 == 0:\n"
            "            out.append('FizzBuzz')\n"
            "        elif i % 3 == 0:\n"
            "            out.append('Fizz')\n"
            "        elif i % 5 == 0:\n"
            "            out.append('Buzz')\n"
            "        else:\n"
            "            out.append(str(i))\n"
            "    return out\n"
        ),
    },
    {
        "name": "merge_intervals",
        "function": "merge_intervals",
        "prompt": (
            "Write a Python function `merge_intervals(intervals)` that takes "
            "a list of [start, end] pairs of integers (start <= end, in any "
            "order) and returns a list of [start, end] lists in which "
            "overlapping or touching intervals are merged, sorted by start. "
            "Intervals that share an endpoint count as touching, so [1, 3] "
            "and [3, 5] merge into [1, 5], but [1, 2] and [3, 4] do not "
            "merge. Return an empty list for empty input.\n\n"
            "Examples:\n"
            "merge_intervals([[1, 3], [2, 6], [8, 10]]) -> [[1, 6], [8, 10]]\n"
            "merge_intervals([[5, 7], [1, 2]]) -> [[1, 2], [5, 7]]\n"
            "merge_intervals([]) -> []\n\n" + REPLY_RULE
        ),
        "generate": _intervals_inputs,
        "reference": (
            "def merge_intervals(intervals):\n"
            "    merged = []\n"
            "    for start, end in sorted(intervals):\n"
            "        if merged and start <= merged[-1][1]:\n"
            "            merged[-1][1] = max(merged[-1][1], end)\n"
            "        else:\n"
            "            merged.append([start, end])\n"
            "    return merged\n"
        ),
    },
]