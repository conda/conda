# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from pathlib import Path
import subprocess

import pytest


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
