from hello_reward import reward


def test_correct_answer_gets_full_score():
    assert reward("4") == 1.0


def test_wrong_answer_gets_zero():
    assert reward("5") == 0.0


def test_answer_with_extra_spaces_still_counts():
    assert reward(" 4 ") == 1.0

def test_answer_in_a_sentence_counts():
    assert reward("The answer is 4.") == 1.0


def test_guessing_many_numbers_does_not_count():
    assert reward("It could be 1, 2, 3, 4 or 5.") == 0.0

def test_empty_answer_gets_zero():
    assert reward("") == 0.0