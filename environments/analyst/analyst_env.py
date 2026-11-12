import random

from analyst_parsing import parse_reply
from analyst_tasks import TASKS, TOLERANCE, make_episode
from run_code_docker import run_python_detailed

MAX_REPLIES = 5
TOOL_TIMEOUT = 5
TOOL_OUTPUT_CHARS = 2000

# This runs INSIDE the sandbox. It writes the data file, then runs the
# model's code. The true answer is never in this program.
HARNESS = r'''
with open("/tmp/data.csv", "w") as _f:
    _f.write(DATA)
exec(compile(CODE, "model_code", "exec"), {"__name__": "__main__"})
'''

INVALID_MESSAGES = {
    "no_action": "INVALID REPLY: it contained neither a python code block nor a FINAL line.",
    "multiple_code_blocks": "INVALID REPLY: it contained more than one code block. Send exactly one.",
    "multiple_final": "INVALID REPLY: it contained more than one FINAL line. Send exactly one.",
    "bad_number": "INVALID REPLY: the FINAL line must hold a single plain number, like FINAL: 42.5.",
}


def build_prompt(episode):
    lines = episode["csv"].splitlines()
    header, n_rows = lines[0], len(lines) - 1
    return (
        "You are analysing a small data table using Python.\n\n"
        f"Question: {episode['question']}\n\n"
        f"The data is a CSV file at /tmp/data.csv. It has {n_rows} rows. "
        f"The first line is the header: {header}\n\n"
        "Each of your replies must be exactly one of these:\n"
        "1. One Markdown code block marked python. It will be run and you "
        "will see what it prints. Only the Python standard library is "
        "available (no pandas or numpy). Every run starts fresh, so nothing "
        "carries over from earlier runs, and each run is limited to 5 seconds.\n"
        "2. One line of the form FINAL: <number> giving your final answer as "
        "a plain number such as 42.5. This ends the task.\n\n"
        f"You have {MAX_REPLIES} replies in total. If you have not given a "
        "FINAL line by your last reply, you score 0. You will not be told "
        "whether your answer is right.\n"
    )


def build_tool_program(csv_text, code):
    """The text sent to the sandbox: the data, the model's code, the harness."""
    return f"DATA = {csv_text!r}\nCODE = {code!r}\n" + HARNESS


def replies_left_text(n):
    if n == 1:
        return "You have 1 reply left. It must contain a FINAL line."
    return f"You have {n} replies left."


class AnalystEnv:
    """Multi-turn tool-use environment: analyse a table with Python, then answer."""

    def __init__(self, seed=0, tasks=None, run_tool=None):
        self.rng = random.Random(seed)
        self.tasks = tasks or TASKS
        self.run_tool = run_tool or run_python_detailed
        self.task = None
        self.episode = None
        self.done = True  # no episode is running yet
        self._reset_counters()

    def _reset_counters(self):
        self.turns = 0
        self.tool_runs = 0
        self.tool_errors = 0
        self.invalid_replies = 0

    def _info(self, reason):
        return {
            "reason": reason,
            "turns": self.turns,
            "tool_runs": self.tool_runs,
            "tool_errors": self.tool_errors,
            "invalid_replies": self.invalid_replies,
        }

    def reset(self):
        """Start a new episode: pick a task, make fresh data, return the prompt."""
        self.task = self.rng.choice(self.tasks)
        episode_seed = self.rng.randrange(2**31)
        self.episode = make_episode(self.task, episode_seed)
        self._reset_counters()
        self.done = False
        return build_prompt(self.episode)

    def step(self, reply):
        """Take one reply. Returns (observation, reward, terminated, truncated, info)."""
        if self.done:
            raise RuntimeError("No active episode: call reset() first")
        self.turns += 1
        left = MAX_REPLIES - self.turns
        kind, payload = parse_reply(reply)

        if kind == "final":
            return self._finish(payload)

        if kind == "invalid":
            self.invalid_replies += 1
            message = INVALID_MESSAGES[payload]
        elif left == 0:
            message = ""  # a tool call on the last turn is not run
        else:
            message = self._run_tool(payload)

        if left == 0:
            self.done = True
            return "", 0.0, False, True, self._info("no_final")
        return message + "\n\n" + replies_left_text(left), 0.0, False, False, self._info(None)

    def _finish(self, value):
        self.done = True
        correct = abs(value - self.episode["answer"]) <= TOLERANCE + 1e-9
        reason = "pass" if correct else "wrong_answer"
        return "", (1.0 if correct else 0.0), True, False, self._info(reason)

    def _run_tool(self, code):
        program = build_tool_program(self.episode["csv"], code)
        status, output = self.run_tool(
            program, timeout=TOOL_TIMEOUT, keep_chars=TOOL_OUTPUT_CHARS
        )
        self.tool_runs += 1
        if status != "ok":
            self.tool_errors += 1
        if status == "timeout":
            return "TOOL: the code ran out of time (limit 5 seconds)."
        if status == "flood":
            return "TOOL: the code produced too much output."
        shown = output if output.strip() else "(no output)"
        return "TOOL OUTPUT:\n" + shown