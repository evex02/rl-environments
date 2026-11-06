import pytest

from stats_utils import wilson_interval


def test_interval_contains_the_observed_rate():
    low, high = wilson_interval(11, 20)
    assert low <= 0.55 <= high


def test_more_episodes_gives_a_narrower_interval():
    low_a, high_a = wilson_interval(11, 20)
    low_b, high_b = wilson_interval(110, 200)
    assert (high_b - low_b) < (high_a - low_a)


def test_zero_successes_still_leaves_some_uncertainty():
    low, high = wilson_interval(0, 20)
    assert low == pytest.approx(0.0, abs=1e-9)
    assert high > 0.0


def test_zero_episodes_raises_an_error():
    with pytest.raises(ValueError):
        wilson_interval(0, 0)