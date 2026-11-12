import sys

import pytest

import run_code_docker
from run_code_docker import docker_command


class _Result:
    returncode = 0


def test_windows_goes_through_wsl(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    assert docker_command() == ["wsl", "-u", "root", "--exec", "docker"]


def test_linux_calls_docker_directly(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    assert docker_command() == ["docker"]


def test_macos_calls_docker_directly(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    assert docker_command() == ["docker"]


def test_docker_works_asks_docker_info(monkeypatch):
    seen = {}

    def fake_run(cmd, **kwargs):
        seen["cmd"] = cmd
        return _Result()

    monkeypatch.setattr(run_code_docker.subprocess, "run", fake_run)
    assert run_code_docker.docker_works() is True
    assert seen["cmd"] == docker_command() + ["info"]


def test_docker_works_is_false_when_the_command_fails(monkeypatch):
    def boom(*args, **kwargs):
        raise FileNotFoundError("no docker here")

    monkeypatch.setattr(run_code_docker.subprocess, "run", boom)
    assert run_code_docker.docker_works() is False


def test_run_command_has_no_wsl_on_linux(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    seen = {}

    def fake_popen(cmd, **kwargs):
        seen["cmd"] = cmd
        raise RuntimeError("stop here")

    monkeypatch.setattr(run_code_docker.subprocess, "Popen", fake_popen)
    with pytest.raises(RuntimeError):
        run_code_docker.run_python_detailed("print(1)")
    assert seen["cmd"][:2] == ["docker", "run"]
    assert "wsl" not in seen["cmd"]


def test_run_command_goes_through_wsl_on_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    seen = {}

    def fake_popen(cmd, **kwargs):
        seen["cmd"] = cmd
        raise RuntimeError("stop here")

    monkeypatch.setattr(run_code_docker.subprocess, "Popen", fake_popen)
    with pytest.raises(RuntimeError):
        run_code_docker.run_python_detailed("print(1)")
    assert seen["cmd"][:6] == ["wsl", "-u", "root", "--exec", "docker", "run"]