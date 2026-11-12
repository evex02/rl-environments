import pytest

from analyst_parsing import parse_reply


def code_reply(code):
    return f"Let me look.\n```python\n{code}\n```"


def test_one_code_block_is_a_tool_call():
    kind, payload = parse_reply(code_reply("print(1)"))
    assert kind == "tool"
    assert payload.strip() == "print(1)"


def test_code_block_without_a_language_tag_still_counts():
    kind, _payload = parse_reply("```\nprint(1)\n```")
    assert kind == "tool"


def test_final_line_is_a_final_answer():
    assert parse_reply("The mean is nice.\nFINAL: 42.5") == ("final", 42.5)


@pytest.mark.parametrize(
    "text,value",
    [
        ("FINAL: 42", 42.0),
        ("FINAL:42", 42.0),
        ("  FINAL:   -3.5  ", -3.5),
        ("FINAL: .5", 0.5),
        ("FINAL: 7.", 7.0),
        ("FINAL: +2", 2.0),
    ],
)
def test_number_formats_that_are_accepted(text, value):
    assert parse_reply(text) == ("final", value)


@pytest.mark.parametrize(
    "text",
    [
        "FINAL: nan",
        "FINAL: inf",
        "FINAL: -inf",
        "FINAL: 3 to 4",
        "FINAL: about 5",
        "FINAL: 12.5%",
        "FINAL: 1e3",
        "FINAL: 1,234",
        "FINAL:",
        "FINAL: " + "9" * 400,
        "FINAL: 4 5",
    ],
)
def test_bad_numbers_are_invalid(text):
    assert parse_reply(text) == ("invalid", "bad_number")


def test_two_final_lines_are_invalid_even_if_equal():
    assert parse_reply("FINAL: 5\nFINAL: 5") == ("invalid", "multiple_final")


def test_two_code_blocks_are_invalid():
    reply = code_reply("print(1)") + "\n" + code_reply("print(2)")
    assert parse_reply(reply) == ("invalid", "multiple_code_blocks")


def test_a_reply_with_neither_is_invalid():
    assert parse_reply("") == ("invalid", "no_action")
    assert parse_reply("I think it is about 5.") == ("invalid", "no_action")


def test_final_wins_over_code_in_the_same_reply():
    reply = code_reply("print(1)") + "\nFINAL: 9"
    assert parse_reply(reply) == ("final", 9.0)


def test_final_text_inside_a_code_block_is_not_an_answer():
    kind, _payload = parse_reply("```python\nFINAL: 9\n```")
    assert kind == "tool"


def test_final_in_the_middle_of_a_line_is_not_an_answer():
    assert parse_reply("so FINAL: 5") == ("invalid", "no_action")


def test_lowercase_final_is_not_accepted():
    assert parse_reply("final: 5") == ("invalid", "no_action")