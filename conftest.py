import os
import subprocess
import time

import pytest


def _docker_responds():
    try:
        result = subprocess.run(
            ["wsl", "-u", "root", "--", "docker", "info"],
            capture_output=True,
            timeout=60,
        )
        return result.returncode == 0
    except Exception:
        return False


def pytest_sessionstart(session):
    """Make sure Docker is answering before any test file is loaded.

    Test files decide at import time whether to skip the Docker tests, so
    Docker has to be responding before that happens. If REQUIRE_DOCKER=1
    and Docker never answers, stop the whole run instead of skipping.
    """
    for _ in range(4):
        if _docker_responds():
            return
        time.sleep(5)
    if os.environ.get("REQUIRE_DOCKER") == "1":
        pytest.exit("REQUIRE_DOCKER=1 but Docker is not responding", returncode=3)