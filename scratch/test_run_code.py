from run_code import run_python


def test_simple_code_runs():
    ok, out = run_python("print('hi')")
    assert ok
    assert out.strip() == "hi"


def test_error_is_reported():
    ok, out = run_python("1/0")
    assert not ok
    assert "ZeroDivisionError" in out


def test_infinite_loop_is_stopped():
    ok, out = run_python("while True: pass", timeout=1)
    assert not ok
    assert out == "timed out"