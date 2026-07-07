# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from conda import plugins
from conda.exceptions import PluginError
from conda.plugins.types import CondaCleanPath


class CleanPathPlugin:
    target_prefix = None

    def find_example_paths(self, target_prefix: str):
        CleanPathPlugin.target_prefix = target_prefix
        return [f"{target_prefix}/example-cache"]

    @plugins.hookimpl
    def conda_clean_paths(self):
        yield CondaCleanPath(
            name="example-cache",
            find=self.find_example_paths,
            summary="Remove example cache files.",
        )


@pytest.fixture()
def clean_path_plugin(plugin_manager):
    plugin = CleanPathPlugin()
    plugin_manager.register(plugin)
    return plugin


def test_clean_path_flag_and_dest():
    clean_path = CondaCleanPath(name="example-cache", find=lambda prefix: ())
    assert clean_path.flag == "--example-cache"
    assert clean_path.dest == "clean_example_cache"


def test_get_clean_paths_sorted(plugin_manager):
    class CleanPathPlugin:
        @plugins.hookimpl
        def conda_clean_paths(self):
            yield CondaCleanPath(name="zebra-cache", find=lambda prefix: ())
            yield CondaCleanPath(name="alpha-cache", find=lambda prefix: ())

    plugin_manager.register(CleanPathPlugin())

    assert list(plugin_manager.get_clean_paths()) == ["alpha-cache", "zebra-cache"]


def test_get_clean_paths(clean_path_plugin, plugin_manager):
    clean_paths = plugin_manager.get_clean_paths()
    assert set(clean_paths) == {"example-cache"}
    assert clean_paths["example-cache"].summary == "Remove example cache files."


def test_find_clean_paths(clean_path_plugin, plugin_manager):
    clean_path = plugin_manager.get_clean_paths()["example-cache"]
    paths = list(clean_path.find("/tmp/prefix"))
    assert paths == ["/tmp/prefix/example-cache"]
    assert CleanPathPlugin.target_prefix == "/tmp/prefix"


def test_conflicting_clean_paths(plugin_manager):
    class FirstCleanPathPlugin:
        @plugins.hookimpl
        def conda_clean_paths(self):
            yield CondaCleanPath(name="example-cache", find=lambda prefix: ())

    class SecondCleanPathPlugin:
        @plugins.hookimpl
        def conda_clean_paths(self):
            yield CondaCleanPath(name="example-cache", find=lambda prefix: ())

    plugin_manager.register(FirstCleanPathPlugin())
    plugin_manager.register(SecondCleanPathPlugin())

    with pytest.raises(
        PluginError, match="Conflicting plugins found for `clean_paths`"
    ):
        plugin_manager.get_clean_paths()
