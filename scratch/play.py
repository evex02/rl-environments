import random
import re

from addition_env import AdditionEnv


def random_player(question, rng):
    """Ignores the question and guesses a number."""
    return f"Answer: {rng.randint(20, 198)}"


def calculator_player(question, rng):
    """Reads the question and adds the numbers properly."""
    a, b = map(int, re.findall(r"\d+", question)[:2])
    return f"Answer: {a + b}"


def average_reward(player, episodes=1000, seed=0):
    """Play many episodes and return the average reward."""
    env = AdditionEnv(seed=seed)
    rng = random.Random(seed)
    total = 0.0
    for _ in range(episodes):
        question = env.reset()
        reply = player(question, rng)
        total += env.step(reply)
    return total / episodes


if __name__ == "__main__":
    print("random player:    ", average_reward(random_player))
    print("calculator player:", average_reward(calculator_player))