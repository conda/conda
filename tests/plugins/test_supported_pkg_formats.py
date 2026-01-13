# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from conda import plugins
from conda.gateways.disk.create import extract_tarball
from conda.plugins.manager import CondaPluginManager
from conda.plugins.types import CondaSupportedPkgFormats


def test_plugin_fetches_correct_extractor(plugin_manager):
    """Test that the correct extractor function is fetched"""

    # pkg extractor function
    def random_extractor(*args, **kwargs):
        pass

    class RandomPkgFormatPlugin:
        @plugins.hookimpl
        def conda_supported_pkg_formats(self):
            yield CondaSupportedPkgFormats(
                name="Random Format", extensions=[".random"], extractor=random_extractor
            )

    # create plugin
    random_pkg_format_plugin = RandomPkgFormatPlugin()

    # register plugin
    plugin_manager.register(random_pkg_format_plugin)

    # test
    extractor = CondaPluginManager.get_pkg_extraction_function_from_plugin(".random")
    assert extractor is random_extractor


def test_plugin_fetches_extract_tarball(plugin_manager):
    extractor = CondaPluginManager.get_pkg_extraction_function_from_plugin(".conda")
    assert extractor is extract_tarball
