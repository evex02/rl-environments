from hello_reward import reward


def test_correct_answer_gets_full_score():
    assert reward("4") == 1.0


def test_wrong_answer_gets_zero():
    assert reward("5") == 0.0


def test_answer_with_extra_spaces_still_counts():
    assert reward(" 4 ") == 1.0