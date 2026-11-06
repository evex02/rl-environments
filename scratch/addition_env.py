import random
import re


class AdditionEnv:
    """A tiny environment: the AI is asked to add two numbers."""

    def __init__(self, seed=0):
        self.rng = random.Random(seed)
        self.correct = None
        self.done = True  # no episode is running yet

    def reset(self):
        """Start a new episode: pick a fresh question and return it."""
        a = self.rng.randint(10, 99)
        b = self.rng.randint(10, 99)
        self.correct = a + b
        self.done = False
        return f"What is {a} + {b}? End your reply with 'Answer: <number>'."

    def step(self, reply):
        """The AI replies; return the reward. Only one reply per episode."""
        if self.done:
            raise RuntimeError("No active episode: call reset() first")
        self.done = True  # the episode ends after one reply
        matches = re.findall(r"answer:\s*(\S+)", reply, flags=re.IGNORECASE)
        if not matches:
            return 0.0
        return 1.0 if matches[-1].rstrip(".") == str(self.correct) else 0.0