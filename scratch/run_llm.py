import random
import re

from openai import OpenAI

from addition_env import AdditionEnv

# Ollama listens on this address on your own computer.
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

FORMAT_REMINDER = (
    "Always finish your reply with a final line in exactly this form:\n"
    "Answer: <number>"
)


def make_llm_player(model, system_prompt=None):
    """Return a player that asks a real AI model to answer the question."""

    def player(question, rng):
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": question})
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=300,
        )
        return response.choices[0].message.content or ""

    return player


def maths_is_right(reply, correct):
    """Lenient check: is the last number in the reply the right one?"""
    numbers = re.findall(r"\d+", reply)
    return bool(numbers) and numbers[-1] == str(correct)


def format_is_followed(reply):
    """Did the reply contain 'Answer: <something>' at all?"""
    return re.search(r"answer:\s*\S+", reply, flags=re.IGNORECASE) is not None


def evaluate(player, episodes=20, seed=0, digits=2):
    """Play many episodes; return (reward, maths right, format followed)."""
    env = AdditionEnv(seed=seed, digits=digits)
    rng = random.Random(seed)
    rewards, maths, formats = 0.0, 0, 0
    for _ in range(episodes):
        question = env.reset()
        reply = player(question, rng)
        maths += maths_is_right(reply, env.correct)
        formats += format_is_followed(reply)
        rewards += env.step(reply)
    return rewards / episodes, maths / episodes, formats / episodes


if __name__ == "__main__":
    model = "llama3.2:1b"
    player = make_llm_player(model, FORMAT_REMINDER)
    for digits in [2, 3, 4, 5]:
        reward, maths, fmt = evaluate(player, digits=digits)
        print(f"{digits}-digit numbers: reward {reward:.2f} | maths right {maths:.2f} | format followed {fmt:.2f}")