# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda.exceptions import InvalidInstaller

from .test_main_env_create import DummyExternalPackagesEnvSpecPlugin

if TYPE_CHECKING:
    from pathlib import Path

    from conda.plugins.manager import CondaPluginManager
    from conda.testing.fixtures import CondaCLIFixture, PathFactoryFixture


def test_env_update_with_invalid_installer(
    conda_cli: CondaCLIFixture,
    tmp_path: Path,
    plugin_manager_with_exporters: CondaPluginManager,
    path_factory: PathFactoryFixture,
) -> None:
    """``conda env update`` raises an error when the installer is invalid."""
    plugin_manager_with_exporters.register(DummyExternalPackagesEnvSpecPlugin())

    (path := tmp_path / "invalid.yml").touch()
    with pytest.raises(InvalidInstaller):
        conda_cli("env", "update", f"--prefix={path_factory()}", f"--file={path}")
