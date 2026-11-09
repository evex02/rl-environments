def _palindrome_inputs(rng, n=20):
    """Fresh test inputs for each episode. Always includes two edge cases."""
    alphabet = "abcdeABCDE123 ,.!?"
    inputs = ["", "a"]
    while len(inputs) < n:
        if rng.random() < 0.5:
            # A palindrome once case and punctuation are ignored.
            half = "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 6)))
            middle = rng.choice(["", "x", "7"])
            inputs.append(half + middle + half[::-1])
        else:
            # Random text, which is usually not a palindrome.
            inputs.append(
                "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 10)))
            )
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
            "is_palindrome('hello') -> False\n\n"
            "Reply with a single Markdown code block marked python that "
            "defines the function."
        ),
        # A function that makes fresh test inputs from a random number generator.
        "generate": _palindrome_inputs,
        "reference": (
            "def is_palindrome(text):\n"
            "    cleaned = [c.lower() for c in text if c.isalnum()]\n"
            "    return cleaned == cleaned[::-1]\n"
        ),
    },
]