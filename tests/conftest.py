# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from pathlib import Path
import subprocess
import sys

import pytest

pytest_plugins = (
    # Add testing fixtures and internal pytest plugins here
    "conda.testing.gateways.fixtures",
    "conda.testing.notices.fixtures",
    "conda.testing.fixtures",
)


def _conda_build_recipe(recipe):
    subprocess.run(
        ["conda-build", str(Path(__file__).resolve().parent / "test-recipes" / recipe)],
        check=True,
    )
    return recipe


@pytest.fixture(scope="session")
def activate_deactivate_package():
    return _conda_build_recipe("activate_deactivate_package")


@pytest.fixture(scope="session")
def pre_link_messages_package():
    return _conda_build_recipe("pre_link_messages_package")


@pytest.fixture
def clear_cache():
    from conda.core.subdir_data import SubdirData

    SubdirData._cache_.clear()


@pytest.fixture()
def support_file_server():
    """
    Open a local web server to test remote support files.
    """
    base = Path(__file__).parents[0] / "conda_env" / "support"
    port = "8928"   # randomly chosen
    proc = subprocess.Popen([sys.executable, "-m", "http.server", "-b", "127.0.0.1", "--directory", base, port])
    yield
    proc.kill()
