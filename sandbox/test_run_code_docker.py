import subprocess

import pytest

from run_code_docker import docker_works, run_python_detailed, run_python_sandboxed


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


def test_fork_bomb_is_contained():
    code = "import os\nwhile True:\n    os.fork()"
    ok, out = run_python_sandboxed(code, timeout=3)
    assert not ok
    # the sandbox must still work afterwards
    ok2, out2 = run_python_sandboxed("print('alive')")
    assert ok2
    assert out2.strip() == "alive"


def test_filling_tmp_is_contained():
    code = (
        "with open('/tmp/big', 'wb') as f:\n"
        "    for _ in range(100):\n"
        "        f.write(b'a' * 1024 * 1024)\n"
        "print('survived')"
    )
    ok, out = run_python_sandboxed(code)
    assert not ok
    assert "survived" not in out


def test_output_flood_is_cut_off():
    code = (
        "import sys\n"
        "chunk = 'a' * 100000\n"
        "for _ in range(2000):\n"
        "    sys.stdout.write(chunk)"
    )
    ok, out = run_python_sandboxed(code)
    assert not ok
    assert out == "output limit exceeded"

def test_output_is_truncated_unless_a_larger_limit_is_requested():
    code = "print('a' * 5000)"
    ok, out = run_python_sandboxed(code)
    assert ok
    assert len(out) == 2000
    ok, out = run_python_sandboxed(code, keep_chars=10_000)
    assert ok
    assert len(out.strip()) == 5000

def test_detailed_status_ok():
    status, out = run_python_detailed("print('hi')")
    assert status == "ok"
    assert out.strip() == "hi"


def test_detailed_status_error():
    status, _out = run_python_detailed("import sys\nsys.exit(3)")
    assert status == "error"


def test_detailed_status_timeout():
    status, _out = run_python_detailed("while True: pass", timeout=2)
    assert status == "timeout"


def test_detailed_status_flood():
    code = "import sys\nfor _ in range(2000):\n    sys.stdout.write('a' * 100000)"
    status, _out = run_python_detailed(code)
    assert status == "flood"


def test_printing_status_words_does_not_change_the_status():
    status, out = run_python_detailed("print('timed out')")
    assert status == "ok"
    assert out.strip() == "timed out"