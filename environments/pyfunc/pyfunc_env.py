import random

from grader import grade
from tasks import TASKS


class PyFuncEnv:
    """Single-turn coding environment: write a function, get graded in a sandbox."""

    def __init__(self, seed=0, tasks=None):
        self.rng = random.Random(seed)
        self.tasks = tasks or TASKS
        self.task = None
        self.episode_seed = None
        self.done = True  # no episode is running yet

    def reset(self):
        """Start a new episode: pick a task and a fresh set of test inputs."""
        self.task = self.rng.choice(self.tasks)
        self.episode_seed = self.rng.randrange(2**31)
        self.done = False
        return self.task["prompt"]

    def step(self, reply):
        """The AI replies; return the reward. Only one reply per episode."""
        if self.done:
            raise RuntimeError("No active episode: call reset() first")
        self.done = True  # the episode ends after one reply
        return grade(reply, self.task, seed=self.episode_seed)