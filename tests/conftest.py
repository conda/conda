# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from pathlib import Path
import subprocess
import sys
import warnings

from conda.testing.fixtures import (
    suppress_resource_warning,
    tmpdir,
    clear_subdir_cache,
)

win_default_shells = ["cmd.exe", "powershell", "git_bash", "cygwin"]
shells = ["bash", "zsh"]
if sys.platform == "win32":
    shells = win_default_shells


def pytest_addoption(parser):
    parser.addoption("--shell", action="append", default=[],
                     help="list of shells to run shell tests on")


def pytest_generate_tests(metafunc):
    if 'shell' in metafunc.fixturenames:
        metafunc.parametrize("shell", metafunc.config.option.shell)


@pytest.fixture(autouse=True)
def suppress_resource_warning():
    """
    Suppress `Unclosed Socket Warning`

    It seems urllib3 keeps a socket open to avoid costly recreation costs.

    xref: https://github.com/kennethreitz/requests/issues/1882
    """
    warnings.filterwarnings("ignore", category=ResourceWarning)


@pytest.fixture(scope='function')
def tmpdir(tmpdir, request):
    tmpdir = TemporaryDirectory(dir=str(tmpdir))
    request.addfinalizer(tmpdir.cleanup)
    return py.path.local(tmpdir.name)


@pytest.fixture(autouse=True)
def clear_subdir_cache():
    SubdirData.clear_cached_local_channel_data()


@pytest.fixture(scope="session", autouse=True)
def conda_build_recipes():
    test_recipes = Path(__file__).resolve().parent / "test-recipes"
    recipes_to_build = ["activate_deactivate_package", "pre_link_messages_package"]
    packages = [str(test_recipes / pkg) for pkg in recipes_to_build]
    cmd = ["conda-build"]
    cmd.extend(packages)
    subprocess.run(cmd, check=True)
