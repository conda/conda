# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pluggy
import pytest
import sys

import conda.cli

from conda.plugins import hooks


@pytest.fixture
def plugin_manager(mocker):
    pm = pluggy.PluginManager('conda')
    pm.add_hookspecs(hooks)
    mocker.patch("conda.base.context.get_plugin_manager", return_value=pm)
    # mocker.patch("conda.base.context.Context.plugin_manager", new=pm)
    return pm


@pytest.fixture
def cli_main(monkeypatch):
    def run_main(*args):
        monkeypatch.setattr(sys, 'argv', ['conda', *args])
        conda.cli.main()
    return run_main
