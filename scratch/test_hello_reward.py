from hello_reward import reward


def test_correct_answer_in_required_format():
    assert reward("Answer: 4") == 1.0


def test_working_then_answer():
    assert reward("2 plus 2 is easy. Answer: 4") == 1.0


def test_extra_spaces_and_full_stop():
    assert reward("  answer:   4.  ") == 1.0


def test_wrong_answer():
    assert reward("Answer: 5") == 0.0


def test_missing_format_gets_zero():
    assert reward("4") == 0.0


def test_hedging_does_not_count():
    assert reward("Answer: 5 or 4") == 0.0


def test_negation_does_not_count():
    assert reward("Answer: not 4") == 0.0


def test_empty_answer_gets_zero():
    assert reward("") == 0.0