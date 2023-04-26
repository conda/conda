# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import sys

import pytest

import conda.cli
from conda.plugins.hookspec import CondaSpecs
from conda.plugins.manager import CondaPluginManager


@pytest.fixture
def plugin_manager(mocker):
    pm = CondaPluginManager()
    pm.add_hookspecs(CondaSpecs)
    mocker.patch("conda.plugins.manager.get_plugin_manager", return_value=pm)
    return pm


@pytest.fixture
def cli_main(monkeypatch):
    def run_main(*args):
        monkeypatch.setattr(sys, "argv", ["conda", *args])
        conda.cli.main()

    return run_main
