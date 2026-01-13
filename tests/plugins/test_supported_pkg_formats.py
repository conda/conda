# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

from conda.plugins.manager import CondaPluginManager

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from conda.testing.fixtures import CondaCLIFixture, TmpEnvFixture


def test_invoked(
    conda_cli: CondaCLIFixture, mocker: MockerFixture, tmp_env: TmpEnvFixture
):
    with tmp_env() as prefix:
        # mocker.patch.object(context.plugin_manager, "get_cached_solver_backend")
        mocked = mocker.patch.object(
            CondaPluginManager, "get_pkg_extraction_function_from_plugin"
        )

        conda_cli("install", f"--prefix={prefix}", "python=3.11", "--yes")

        mocked.assert_called()
