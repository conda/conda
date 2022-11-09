# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pluggy
import pytest
import sys

import conda.cli

from conda.plugins.manager import CondaPluginManager
from conda.plugins.hookspec import CondaSpecs


@pytest.fixture
def plugin_manager(mocker):
    pm = CondaPluginManager()
    pm.add_hookspecs(CondaSpecs)
    mocker.patch("conda.core.index.get_plugin_manager", return_value=pm)
    mocker.patch("conda.cli.conda_argparse.get_plugin_manager", return_value=pm)
    return pm


@pytest.fixture
def cli_main(monkeypatch):
    def run_main(*args):
        monkeypatch.setattr(sys, "argv", ["conda", *args])
        conda.cli.main()

    return run_main
