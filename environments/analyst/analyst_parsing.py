import math
import re

CODE_BLOCK = re.compile(r"```(?:python|py)?[ \t]*\n(.*?)```", re.DOTALL | re.IGNORECASE)
FINAL_LINE = re.compile(r"^[ \t]*FINAL:[ \t]*(.*?)[ \t]*$", re.MULTILINE)
PLAIN_NUMBER = re.compile(r"[+-]?(\d+(\.\d*)?|\.\d+)")


def parse_reply(reply):
    """Classify one reply from the model.

    Returns one of:
      ("tool", code)        exactly one code block and no FINAL line
      ("final", number)     exactly one valid FINAL line (any code is ignored)
      ("invalid", reason)   reason is one of: no_action, multiple_code_blocks,
                            multiple_final, bad_number
    """
    text = reply.replace("\r\n", "\n")
    blocks = CODE_BLOCK.findall(text)
    outside_code = CODE_BLOCK.sub("", text)
    finals = FINAL_LINE.findall(outside_code)

    if len(finals) > 1:
        return "invalid", "multiple_final"
    if len(finals) == 1:
        value = finals[0]
        if not PLAIN_NUMBER.fullmatch(value):
            return "invalid", "bad_number"
        number = float(value)
        if not math.isfinite(number):
            return "invalid", "bad_number"
        return "final", number
    if len(blocks) > 1:
        return "invalid", "multiple_code_blocks"
    if len(blocks) == 1:
        return "tool", blocks[0]
    return "invalid", "no_action"