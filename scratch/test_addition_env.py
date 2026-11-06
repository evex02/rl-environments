from addition_env import AdditionEnv


def test_reset_gives_a_question():
    env = AdditionEnv(seed=1)
    question = env.reset()
    assert "What is" in question


def test_correct_reply_gets_full_score():
    env = AdditionEnv(seed=1)
    env.reset()
    assert env.step(f"Answer: {env.correct}") == 1.0


def test_wrong_reply_gets_zero():
    env = AdditionEnv(seed=1)
    env.reset()
    assert env.step(f"Answer: {env.correct + 1}") == 0.0


def test_same_seed_gives_same_question():
    assert AdditionEnv(seed=7).reset() == AdditionEnv(seed=7).reset()