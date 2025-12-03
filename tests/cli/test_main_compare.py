# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from contextlib import nullcontext
from typing import TYPE_CHECKING

import pytest

from conda.cli import main_compare
from conda.cli.main_compare import get_packages
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
        assert {
            package.name: package for package in get_packages(prefix)
        } == prefix_data.map_records()


@pytest.mark.parametrize(
    "function,raises",
    [
        ("get_packages", TypeError),
    ],
)
def test_deprecations(function: str, raises: type[Exception] | None) -> None:
    raises_context = pytest.raises(raises) if raises else nullcontext()
    with pytest.deprecated_call(), raises_context:
        getattr(main_compare, function)()
