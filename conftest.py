import os
import time

import pytest


def pytest_sessionstart(session):
    """Make sure Docker is answering before any test file is loaded.

    Test files decide at import time whether to skip the Docker tests, so
    Docker has to be responding before that happens. If REQUIRE_DOCKER=1
    and Docker never answers, stop the whole run instead of skipping.
    """
    from run_code_docker import docker_works

    for _ in range(4):
        if docker_works(timeout=60):
            return
        time.sleep(5)
    if os.environ.get("REQUIRE_DOCKER") == "1":
        pytest.exit("REQUIRE_DOCKER=1 but Docker is not responding", returncode=3)