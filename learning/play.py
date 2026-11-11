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

def sloppy_player(question, rng, error_rate=0.3):
    """Adds correctly most of the time, but sometimes slips by a little."""
    a, b = map(int, re.findall(r"\d+", question)[:2])
    total = a + b
    if rng.random() < error_rate:
        total += rng.choice([-10, -1, 1, 10])
    return f"Answer: {total}"


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
    print("sloppy player:    ", average_reward(sloppy_player))
    print("calculator player:", average_reward(calculator_player))