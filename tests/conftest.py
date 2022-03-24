# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from pathlib import Path
import subprocess

import pytest


def _conda_build_recipe(pkg):
    subprocess.run(
        ["conda-build", Path(__file__).resolve().parent / "test-recipes" / pkg],
        check=True,
    )


@pytest.fixture(scope="session")
def activate_deactivate_package():
    pkg = "activate_deactivate_package"
    _conda_build_recipe(pkg)
    return pkg


@pytest.fixture(scope="session")
def pre_link_messages_package():
    pkg = "pre_link_messages_package"
    _conda_build_recipe(pkg)
    return pkg
