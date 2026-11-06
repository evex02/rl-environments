import re


def reward(answer):
    """Scores an answer to 'What is 2 + 2?'.

    The task tells the AI to finish with 'Answer: <number>'.
    Only the text after the last 'Answer:' is scored.
    """
    matches = re.findall(r"answer:\s*(\S+)", answer, flags=re.IGNORECASE)
    if not matches:
        return 0.0  # no answer in the required format
    return 1.0 if matches[-1].rstrip(".") == "4" else 0.0