# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda.core.prefix_data import PrefixData
from conda.exceptions import EnvironmentLocationNotFound

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

    from conda.testing.fixtures import CondaCLIFixture, TmpEnvFixture


def test_compare(mocker: MockerFixture, tmp_path: Path, conda_cli: CondaCLIFixture):
    mocked = mocker.patch(
        "conda.base.context.mockable_context_envs_dirs",
        return_value=(str(tmp_path),),
    )

    with pytest.raises(EnvironmentLocationNotFound):
        conda_cli("compare", "--name", "nonexistent", "tempfile.rc", "--json")

    assert mocked.call_count > 0


def test_get_packages(test_recipes_channel: Path, tmp_env: TmpEnvFixture):
    with tmp_env("dependent") as prefix:
        prefix_data = PrefixData(prefix, interoperability=True)

        assert prefix_data.get("dependent")
        assert len(list(prefix_data.iter_records())) == 2

        records = prefix_data.map_records()

        assert len(records) == 2
        assert "dependent" in records
