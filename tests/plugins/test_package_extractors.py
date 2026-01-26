# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from contextlib import nullcontext
from typing import TYPE_CHECKING

import pytest

from conda import plugins
from conda.base.context import context
from conda.exceptions import PluginError
from conda.plugins.package_extractors.conda import extract_conda_or_tarball
from conda.plugins.types import CondaPackageExtractor

from .. import TEST_RECIPES_CHANNEL

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

    from conda.plugins.manager import CondaPluginManager


@pytest.fixture
def extractor_plugin(
    plugin_manager: CondaPluginManager, mocker: MockerFixture
) -> CondaPackageExtractor:
    """Returns a random package extractor plugin for testing."""
    return CondaPackageExtractor(
        name="random-package",
        extensions=[".random", ".UPPER"],
        extract=mocker.stub(name="random_extractor"),
    )


@pytest.fixture
def extractor_plugin_manager(
    extractor_plugin: CondaPackageExtractor, plugin_manager: CondaPluginManager
) -> CondaPluginManager:
    """Returns a plugin manager with a random package extractor plugin registered."""

    class RandomExtractorPlugin:
        """Test plugin that registers a random package extractor."""

        @plugins.hookimpl
        def conda_package_extractors(self):
            yield extractor_plugin

    plugin_manager.register(RandomExtractorPlugin())
    return plugin_manager


def test_plugin_fetches_correct_extractor(
    extractor_plugin_manager: CondaPluginManager,
    extractor_plugin: CondaPackageExtractor,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    """Test that a custom plugin extractor is correctly registered, fetched, and invoked."""
    source = tmp_path / "source.random"
    extractor_plugin_manager.extract_package(source, tmp_path)
    assert extractor_plugin.extract.call_count == 1


@pytest.mark.parametrize(
    "extension,raises",
    [
        (".conda", None),
        (".tar.bz2", None),
        (".not_supported", PluginError),
    ],
)
def test_get_package_extractor(
    extension: str,
    raises: type[Exception] | None,
) -> None:
    """Test that get_package_extractor returns the correct extractor or raises for unsupported formats."""
    with pytest.raises(raises) if raises else nullcontext():
        extractor = context.plugin_manager.get_package_extractor(
            f"something{extension}"
        )
        assert extractor.extract is extract_conda_or_tarball


def test_extract_package(tmp_path: Path) -> None:
    """Test that extract_package correctly extracts a .conda package."""
    package_path = TEST_RECIPES_CHANNEL / "noarch" / "small-executable-1.0.0-0.conda"
    destination = tmp_path / "extracted"

    context.plugin_manager.extract_package(package_path, destination)

    # Verify extraction produced expected files from small-executable package.
    # Since this is a noarch package, bin/small is present on all platforms.
    assert destination.exists()
    assert (destination / "bin" / "small").exists()
    assert (
        destination / "etc" / "conda" / "activate.d" / "small_executable.sh"
    ).exists()


def test_get_package_extractors(
    extractor_plugin_manager: CondaPluginManager,
    extractor_plugin: CondaPackageExtractor,
) -> None:
    """Test that get_package_extractors returns a dict mapping extensions to extractors."""
    extractors = extractor_plugin_manager.get_package_extractors()

    # Should return a dict
    assert isinstance(extractors, dict)

    # Should contain our registered extensions (lowercased)
    assert ".random" in extractors
    assert ".upper" in extractors  # .UPPER becomes .upper

    # Keys should be lowercased, values should be CondaPackageExtractor instances
    for extension, extractor in extractors.items():
        assert extension == extension.lower()
        assert isinstance(extractor, CondaPackageExtractor)


@pytest.mark.parametrize(
    "path,expected",
    [
        ("package.random", ".random"),
        ("/path/to/package.random", ".random"),
        ("package.RANDOM", ".random"),  # case insensitive, returns lowercased
        ("package.upper", ".upper"),
        ("package.UPPER", ".upper"),  # case insensitive, returns lowercased
        ("package.other", None),
        ("package", None),
        ("", None),
    ],
)
def test_has_package_extension(
    extractor_plugin_manager: CondaPluginManager,
    path: str,
    expected: str | None,
) -> None:
    """Test that has_package_extension returns the matched extension or None."""
    assert extractor_plugin_manager.has_package_extension(path) == expected
