# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from conda.plugins.hookspec import CondaSpecs
from conda.plugins.manager import CondaPluginManager


@pytest.fixture
def plugin_manager(mocker) -> CondaPluginManager:
    pm = CondaPluginManager()
    pm.add_hookspecs(CondaSpecs)
    mocker.patch("conda.plugins.manager.get_plugin_manager", return_value=pm)
    return pm
