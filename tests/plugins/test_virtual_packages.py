import re
import textwrap

import conda.core.index
import conda.exceptions
from conda.base.context import context
from conda import plugins

import pytest


class VirtualPackagesPlugin:
        @plugins.hookimp
        def conda_cli_register_virtual_packages(self):
            yield plugins.CondaVirtualPackage(
                name='abc',
                version='123',
            )
            yield plugins.CondaVirtualPackage(
                name='def',
                version='456',
            )
            yield plugins.CondaVirtualPackage(
                name='ghi',
                version='789',
            )


@pytest.fixture()
def plugin(plugin_manager):
    plugin = VirtualPackagesPlugin()
    plugin_manager.register(plugin)
    return plugin


def test_invoked(plugin, cli_main):
    index = conda.core.index.get_reduced_index(
        context.default_prefix,
        context.default_channels,
        context.subdirs,
        (),
        context.repodata_fns[0],
    )

    assert index['__abc'].version == '123'
    assert index['__def'].version == '456'
    assert index['__ghi'].version == '789'


def test_duplicated(plugin_manager, cli_main, capsys):
    plugin_manager.register(VirtualPackagesPlugin())
    plugin_manager.register(VirtualPackagesPlugin())

    with pytest.raises(conda.exceptions.PluginError, match=re.escape(
        'Conflicting virtual package entries found for the '
        '`custom` subcommand. Multiple Conda plugins '
        'are registering this virtual package via the '
        '`conda_cli_register_virtual_packages` hook, please make sure '
        'you don\'t have any incompatible plugins installed.'
    )):
        conda.core.index.get_reduced_index(
            context.default_prefix,
            context.default_channels,
            context.subdirs,
            (),
            context.repodata_fns[0],
        )
