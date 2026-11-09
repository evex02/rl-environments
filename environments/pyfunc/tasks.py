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
        # (input, expected answer). Single-argument functions for now.
        "cases": [
            ("", True),
            ("a", True),
            ("Was it a car or a cat I saw?", True),
            ("No lemon, no melon", True),
            ("12321", True),
            ("abca", False),
            ("12345", False),
            ("ab", False),
        ],
        "reference": (
            "def is_palindrome(text):\n"
            "    cleaned = [c.lower() for c in text if c.isalnum()]\n"
            "    return cleaned == cleaned[::-1]\n"
        ),
    },
]