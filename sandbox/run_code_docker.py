import subprocess
import threading
import time
import uuid

IMAGE = "python:3.12-slim"
MAX_OUTPUT_BYTES = 100_000  # more output than this counts as a flood
KEEP_CHARS = 2000           # default amount of output we hand back

# This runs INSIDE the container. The program's output goes into a file in
# the small /tmp area, then only the first MAX_OUTPUT_BYTES + 1 bytes are
# sent back. The extra byte lets us tell "exactly at the limit" from
# "over the limit".
INNER_SCRIPT = (
    "timeout {timeout} python - > /tmp/out 2>&1; "
    "code=$?; "
    "head -c {cap} /tmp/out; "
    "exit $code"
)


def _remove_container(name):
    subprocess.run(
        ["wsl", "-u", "root", "--", "docker", "rm", "-f", name],
        capture_output=True,
    )


def run_python_detailed(code, timeout=5, keep_chars=KEEP_CHARS):
    """Run untrusted Python code in a locked-down Docker container.

    Returns (status, output). The status is decided by the runner, never by
    anything the program prints:
      "ok"       the program exited with code 0
      "error"    it exited with any other code
      "timeout"  it ran out of time
      "flood"    it produced more than MAX_OUTPUT_BYTES of output
    """
    name = f"sandbox-{uuid.uuid4().hex[:12]}"
    inner = INNER_SCRIPT.format(timeout=timeout, cap=MAX_OUTPUT_BYTES + 1)
    cmd = [
        "wsl", "-u", "root", "--exec",
        "docker", "run", "--rm", "-i",
        "--name", name,
        "--network", "none",
        "--read-only",
        "--tmpfs", "/tmp:rw,size=16m",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--pids-limit", "64",
        "--memory", "128m",
        "--memory-swap", "128m",
        "--cpus", "1",
        "--user", "65534:65534",
        IMAGE,
        "sh", "-c", inner,
    ]
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    # Backstop: if anything hangs, remove the container after a while.
    fired = {"yes": False}

    def backstop():
        fired["yes"] = True
        _remove_container(name)

    timer = threading.Timer(timeout + 15, backstop)
    timer.start()

    chunks, total, flooded = [], 0, False
    try:
        try:
            proc.stdin.write(code.encode("utf-8"))
            proc.stdin.close()
        except (BrokenPipeError, OSError):
            pass  # the program already ended, which is fine
        while True:
            chunk = proc.stdout.read1(65536)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_OUTPUT_BYTES:
                flooded = True
                break
            chunks.append(chunk)
    finally:
        timer.cancel()

    if flooded:
        _remove_container(name)
        proc.kill()
        proc.wait()
        return "flood", ""

    proc.wait()
    if fired["yes"] or proc.returncode == 124:  # 124 = 'timeout' fired
        return "timeout", ""
    output = b"".join(chunks).decode("utf-8", errors="replace")[:keep_chars]
    return ("ok" if proc.returncode == 0 else "error"), output


def run_python_sandboxed(code, timeout=5, keep_chars=KEEP_CHARS):
    """Older interface: (ok, output). Kept so existing tests and scripts work.

    For timeouts and floods it returns a fixed text message. Anything that
    needs to tell those apart from real program output must use
    run_python_detailed instead.
    """
    status, output = run_python_detailed(code, timeout, keep_chars)
    if status == "timeout":
        return False, "timed out"
    if status == "flood":
        return False, "output limit exceeded"
    return status == "ok", output