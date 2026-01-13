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
    mocked_extractor = mocker.Mock(name="extractor")
    mocked_extractor.return_value = "extractor"

    mocked = mocker.patch.object(
        CondaPluginManager,
        "get_pkg_extraction_function_from_plugin",
        return_value=mocked_extractor,
    )

    conda_cli("install", "numpy", "--yes")

    mocked.assert_called()
    mocked_extractor.assert_called()
