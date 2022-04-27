# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pluggy
import pytest
import sys

import conda.cli

from conda import plugins


@pytest.fixture
def plugin_manager(mocker):
    plugin_manager = pluggy.PluginManager('conda')
    plugin_manager.add_hookspecs(plugins)
    mocker.patch('conda.base.context.get_plugin_manager', return_value=plugin_manager)
    return plugin_manager


@pytest.fixture
def cli_main(monkeypatch):
    def run_main(*args):
        monkeypatch.setattr(sys, 'argv', ['conda', *args])
        conda.cli.main()
    return run_main
