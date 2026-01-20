# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import pytest

from conda import plugins
from conda.base.context import context
from conda.exceptions import PluginError
from conda.plugins.package_extractors.conda_pkg import extract_conda_or_tarball
from conda.plugins.types import CondaPackageExtractor


def test_plugin_fetches_correct_extractor(plugin_manager):
    """Test that the correct extractor function is fetched"""

    # pkg extractor function
    def random_extractor(*args, **kwargs):
        pass

    class RandomPkgFormatPlugin:
        @plugins.hookimpl
        def conda_package_extractors(self):
            yield CondaPackageExtractor(
                name="Random Format", extensions=[".random"], extract=random_extractor
            )

    # create plugin
    random_pkg_format_plugin = RandomPkgFormatPlugin()

    # register plugin
    plugin_manager.register(random_pkg_format_plugin)

    # test
    extractor = context.plugin_manager.get_package_extractor("something.random")
    assert extractor.extract is random_extractor


def test_plugin_fetches_extract_tarball():
    extractor = context.plugin_manager.get_package_extractor("something.conda")
    assert extractor.extract is extract_conda_or_tarball


def test_plugin_raises_error_for_unsupported_format():
    with pytest.raises(PluginError):
        context.plugin_manager.get_package_extractor("something.not_supported")


def test_conda_pkg_extraction(): ...
