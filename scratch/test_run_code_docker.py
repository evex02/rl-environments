import subprocess

import pytest

from run_code_docker import run_python_sandboxed


def docker_works():
    try:
        result = subprocess.run(
            ["wsl", "-u", "root", "--", "docker", "info"],
            capture_output=True,
            timeout=30,
        )
        return result.returncode == 0
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not docker_works(), reason="Docker not available")


def test_simple_code_runs():
    ok, out = run_python_sandboxed("print('hi')")
    assert ok
    assert out.strip() == "hi"


def test_runs_as_non_root():
    ok, out = run_python_sandboxed("import os; print(os.getuid())")
    assert ok
    assert out.strip() == "65534"


def test_network_is_blocked():
    code = "import urllib.request; urllib.request.urlopen('http://example.com', timeout=3)"
    ok, out = run_python_sandboxed(code)
    assert not ok


def test_host_files_are_not_visible():
    ok, out = run_python_sandboxed("import os; print(os.listdir('/'))")
    assert ok
    assert "scratch" not in out
    assert "journal.md" not in out


def test_cannot_write_outside_tmp():
    ok, out = run_python_sandboxed("open('/etc/pwned.txt', 'w').write('x')")
    assert not ok


def test_can_write_to_tmp():
    ok, out = run_python_sandboxed("open('/tmp/ok.txt', 'w').write('x'); print('done')")
    assert ok
    assert "done" in out


def test_infinite_loop_is_stopped():
    ok, out = run_python_sandboxed("while True: pass", timeout=2)
    assert not ok
    assert out == "timed out"


def test_memory_hog_is_killed():
    ok, out = run_python_sandboxed("x = b'a' * (400 * 1024 * 1024); print('survived')")
    assert not ok
    assert "survived" not in out