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
    manager = pluggy.PluginManager("conda")
    manager.add_hookspecs(plugins.specs)
    mocker.patch(
        "conda.plugins.manager",
        manager,
    )
    return manager


@pytest.fixture
def cli_main(monkeypatch):
    def run_main(*args):
        monkeypatch.setattr(sys, 'argv', ['conda', *args])
        conda.cli.main()
    return run_main
