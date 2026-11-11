from play import average_reward, calculator_player, random_player, sloppy_player

def test_calculator_player_scores_perfectly():
    assert average_reward(calculator_player, episodes=100) == 1.0


def test_random_player_scores_near_zero():
    assert average_reward(random_player, episodes=1000) < 0.05

def test_sloppy_player_scores_in_the_middle():
    score = average_reward(sloppy_player, episodes=1000)
    assert 0.6 < score < 0.8