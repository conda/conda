# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

from contextlib import nullcontext
from typing import TYPE_CHECKING

import pytest
from binstar_client.errors import NotFound

from conda.env.env import Environment
from conda.env.specs import binstar

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_name_not_present():
    """No name provided."""
    spec = binstar.BinstarSpec()
    assert not spec.package
    assert not spec.can_handle()
    assert spec.msg == "Can't process without a name"


def test_invalid_name():
    """Invalid name provided."""
    spec = binstar.BinstarSpec("invalid-name")
    assert not spec.package
    assert not spec.can_handle()
    assert spec.msg == "Invalid name 'invalid-name', try the format: user/package"


def test_package_not_exist(mocker: MockerFixture):
    """Package doesn't exist."""
    mocker.patch(
        "conda.env.specs.binstar.BinstarSpec.binstar",
        new_callable=mocker.PropertyMock,
        return_value=mocker.MagicMock(
            package=mocker.MagicMock(side_effect=NotFound("msg"))
        ),
    )

    spec = binstar.BinstarSpec("darth/no-exist")
    assert not spec.package
    assert not spec.can_handle()


def test_package_without_environment_file(mocker: MockerFixture):
    """Package exists but no environment file is present."""
    mocker.patch(
        "conda.env.specs.binstar.BinstarSpec.binstar",
        new_callable=mocker.PropertyMock,
        return_value=mocker.MagicMock(
            package=mocker.MagicMock(return_value={"files": []})
        ),
    )

    spec = binstar.BinstarSpec("darth/no-env-file")
    assert spec.package
    assert not spec.can_handle()


def test_download_environment(mocker: MockerFixture):
    """Package exists with an environment file."""
    mocker.patch(
        "conda.env.specs.binstar.BinstarSpec.binstar",
        new_callable=mocker.PropertyMock,
        return_value=mocker.MagicMock(
            package=mocker.MagicMock(
                return_value={
                    "files": [
                        {"type": "env", "version": "1", "basename": "environment.yml"}
                    ],
                },
            ),
            download=mocker.MagicMock(return_value=mocker.MagicMock(text="name: env")),
        ),
    )

    spec = binstar.BinstarSpec("darth/env-file")
    assert spec.package
    assert spec.can_handle()
    assert isinstance(spec.environment, Environment)


def test_environment_version_sorting(mocker: MockerFixture):
    """Package exists with multiple environment files, get latest version."""
    downloader = mocker.MagicMock(return_value=mocker.MagicMock(text="name: env"))
    mocker.patch(
        "conda.env.specs.binstar.BinstarSpec.binstar",
        new_callable=mocker.PropertyMock,
        return_value=mocker.MagicMock(
            package=mocker.MagicMock(
                return_value={
                    "files": [
                        {
                            "type": "env",
                            "version": "0.1.1",
                            "basename": "environment.yml",
                        },
                        {
                            "type": "env",
                            "version": "0.1a.2",
                            "basename": "environment.yml",
                        },
                        {
                            "type": "env",
                            "version": "0.2.0",
                            "basename": "environment.yml",
                        },
                    ],
                },
            ),
            download=downloader,
        ),
    )

    spec = binstar.BinstarSpec("darth/env-file")
    assert spec.package
    assert spec.can_handle()
    assert isinstance(spec.environment, Environment)
    downloader.assert_called_with("darth", "env-file", "0.2.0", "environment.yml")


def test_binstar_not_installed(mocker: MockerFixture):
    """Mock anaconda-client not installed."""
    mocker.patch(
        "conda.env.specs.binstar.BinstarSpec.binstar",
        new_callable=mocker.PropertyMock,
        return_value=None,
    )

    spec = binstar.BinstarSpec("user/package")
    assert not spec.package
    assert not spec.can_handle()
    assert spec.msg == (
        "Anaconda Client is required to interact with anaconda.org or an Anaconda API. "
        "Please run `conda install anaconda-client -n base`."
    )


@pytest.mark.parametrize(
    "function,raises",
    [
        ("ENVIRONMENT_TYPE", TypeError),
        ("BinstarSpec", None),
    ],
)
def test_deprecations(function: str, raises: type[Exception] | None) -> None:
    raises_context = pytest.raises(raises) if raises else nullcontext()
    with pytest.deprecated_call(), raises_context:
        getattr(binstar, function)()
