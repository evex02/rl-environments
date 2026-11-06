from play import average_reward, calculator_player, random_player


def test_calculator_player_scores_perfectly():
    assert average_reward(calculator_player, episodes=100) == 1.0


def test_random_player_scores_near_zero():
    assert average_reward(random_player, episodes=1000) < 0.05