# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from pathlib import Path
import subprocess
import sys

import pytest

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


@pytest.fixture(scope="session", autouse=True)
def conda_build_recipes():
    test_recipes = Path(__file__).resolve().parent / "test-recipes"
    recipes_to_build = ["activate_deactivate_package", "pre_link_messages_package"]
    packages = [str(test_recipes / pkg) for pkg in recipes_to_build]
    cmd = ["conda-build"]
    cmd.extend(packages)
    subprocess.run(cmd, check=True)
