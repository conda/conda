import sys

import conda.cli

from conda import plugins

import pluggy
import pytest


@pytest.fixture()
def plugin_manager(mocker):
    pm = pluggy.PluginManager('conda')
    pm.add_hookspecs(plugins)

    mocker.patch('conda.base.context.get_plugin_manager', return_value=pm)

    return pm


@pytest.fixture()
def cli_main(monkeypatch):
    def run_main(*args):
        monkeypatch.setattr(sys, 'argv', ['conda', *args])
        conda.cli.main()
    return run_main
