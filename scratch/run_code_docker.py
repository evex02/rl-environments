import subprocess
import uuid

IMAGE = "python:3.12-slim"


def run_python_sandboxed(code, timeout=5):
    """Run untrusted Python code inside a locked-down Docker container."""
    name = f"sandbox-{uuid.uuid4().hex[:12]}"
    cmd = [
        "wsl", "-u", "root", "--",
        "docker", "run", "--rm", "-i",
        "--name", name,
        "--network", "none",              # no internet
        "--read-only",                    # container's files can't be changed...
        "--tmpfs", "/tmp:rw,size=16m",    # ...except a small scratch area
        "--cap-drop", "ALL",              # no special Linux powers
        "--security-opt", "no-new-privileges",
        "--pids-limit", "64",             # caps how many processes it can start
        "--memory", "128m",               # memory limit
        "--memory-swap", "128m",          # no extra swap memory
        "--cpus", "1",
        "--user", "65534:65534",          # not an administrator inside
        IMAGE,
        "timeout", str(timeout), "python", "-",   # time limit, code from stdin
    ]
    try:
        result = subprocess.run(
            cmd,
            input=code,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout + 15,
        )
    except subprocess.TimeoutExpired:
        # Stopping our command doesn't stop the container, so remove it.
        subprocess.run(
            ["wsl", "-u", "root", "--", "docker", "rm", "-f", name],
            capture_output=True,
        )
        return False, "timed out"
    if result.returncode == 124:  # the code that 'timeout' uses when it fires
        return False, "timed out"
    output = (result.stdout + result.stderr)[:2000]
    return result.returncode == 0, output