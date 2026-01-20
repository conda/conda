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


def test_plugin_fetches_correct_extractor(
    plugin_manager: CondaPluginManager,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    """Test that a custom plugin extractor is correctly registered, fetched, and invoked."""
    random_extractor = mocker.stub(name="random_extractor")

    class RandomPkgFormatPlugin:
        @plugins.hookimpl
        def conda_package_extractors(self):
            yield CondaPackageExtractor(
                name="random-package",
                extensions=[".random"],
                extract=random_extractor,
            )

    plugin_manager.register(RandomPkgFormatPlugin())

    # Verify the correct extractor is fetched
    source = tmp_path / "source.random"
    extractor = context.plugin_manager.get_package_extractor(source)
    assert extractor.extract is random_extractor

    # Verify extract_package invokes the correct extractor
    context.plugin_manager.extract_package(source, tmp_path)
    assert random_extractor.call_count == 1


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
