import subprocess
import sys


def run_python(code, timeout=5):
    """Run Python code in a separate process; return (ok, output)."""
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, "timed out"
    output = (result.stdout + result.stderr)[:2000]
    return result.returncode == 0, output