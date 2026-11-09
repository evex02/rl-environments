import subprocess
import threading
import uuid

IMAGE = "python:3.12-slim"
MAX_OUTPUT_BYTES = 100_000  # more output than this counts as a flood
KEEP_CHARS = 2000           # how much output we hand back

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


def run_python_sandboxed(code, timeout=5, keep_chars=KEEP_CHARS):
    """Run untrusted Python code inside a locked-down Docker container."""
    name = f"sandbox-{uuid.uuid4().hex[:12]}"
    inner = INNER_SCRIPT.format(timeout=timeout, cap=MAX_OUTPUT_BYTES + 1)
    cmd = [
        "wsl", "-u", "root", "--exec",   # --exec: no extra shell in between
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
        return False, "output limit exceeded"

    proc.wait()
    if fired["yes"] or proc.returncode == 124:  # 124 = 'timeout' fired
        return False, "timed out"
    output = b"".join(chunks).decode("utf-8", errors="replace")[:keep_chars]
    return proc.returncode == 0, output