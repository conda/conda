# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from contextlib import nullcontext
from typing import TYPE_CHECKING

import pytest

from conda.base.constants import PREFIX_FROZEN_FILE
from conda.exceptions import CondaValueError
from conda.gateways.disk import create

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


@pytest.mark.parametrize(
    ("env_var", "path_parts"),
    (
        pytest.param("_CONDA_ROOT", (), id="conda-root"),
        pytest.param("CONDA_EXE", ("bin", "conda"), id="conda-exe"),
    ),
)
def test_first_writable_envs_dir_rejects_env_local_conda_nested_env(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    env_var: str,
    path_parts: tuple[str, ...],
) -> None:
    base_prefix = tmp_path / "miniconda3"
    active_prefix = base_prefix / "envs" / "default"
    envs_dir = active_prefix / "envs"
    frozen_file = base_prefix / PREFIX_FROZEN_FILE

    mocker.patch(
        "conda.base.context.Context.active_prefix",
        new_callable=mocker.PropertyMock,
        return_value=str(active_prefix),
    )
    mocker.patch(
        "conda.base.context.Context.conda_prefix",
        new_callable=mocker.PropertyMock,
        return_value=str(active_prefix),
    )
    mocker.patch(
        "conda.base.context.Context.envs_dirs",
        new_callable=mocker.PropertyMock,
        return_value=(str(envs_dir),),
    )
    monkeypatch.delenv("_CONDA_ROOT", raising=False)
    monkeypatch.delenv("CONDA_EXE", raising=False)
    monkeypatch.setenv(env_var, str(base_prefix.joinpath(*path_parts)))
    frozen_file.parent.mkdir(parents=True)
    frozen_file.touch()

    with pytest.raises(
        CondaValueError,
        match="Refusing to create a named environment",
    ):
        create.first_writable_envs_dir(reject_active_envs_dir=True)

    assert not envs_dir.exists()


def test_first_writable_envs_dir_allows_unprotected_base_env_local_conda(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    base_prefix = tmp_path / "miniconda3"
    active_prefix = base_prefix / "envs" / "default"
    envs_dir = active_prefix / "envs"

    mocker.patch(
        "conda.base.context.Context.active_prefix",
        new_callable=mocker.PropertyMock,
        return_value=str(active_prefix),
    )
    mocker.patch(
        "conda.base.context.Context.conda_prefix",
        new_callable=mocker.PropertyMock,
        return_value=str(active_prefix),
    )
    mocker.patch(
        "conda.base.context.Context.envs_dirs",
        new_callable=mocker.PropertyMock,
        return_value=(str(envs_dir),),
    )
    monkeypatch.delenv("_CONDA_ROOT", raising=False)
    monkeypatch.setenv("CONDA_EXE", str(base_prefix / "bin" / "conda"))

    assert create.first_writable_envs_dir(reject_active_envs_dir=True) == str(envs_dir)
    assert (envs_dir / ".conda_envs_dir_test").is_file()


def test_first_writable_envs_dir_allows_safe_envs_dir_with_env_local_conda(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    base_prefix = tmp_path / "miniconda3"
    active_prefix = base_prefix / "envs" / "default"
    safe_envs_dir = tmp_path / "safe-envs"

    mocker.patch(
        "conda.base.context.Context.active_prefix",
        new_callable=mocker.PropertyMock,
        return_value=str(active_prefix),
    )
    mocker.patch(
        "conda.base.context.Context.conda_prefix",
        new_callable=mocker.PropertyMock,
        return_value=str(active_prefix),
    )
    mocker.patch(
        "conda.base.context.Context.envs_dirs",
        new_callable=mocker.PropertyMock,
        return_value=(str(safe_envs_dir), str(active_prefix / "envs")),
    )
    monkeypatch.delenv("_CONDA_ROOT", raising=False)
    monkeypatch.setenv("CONDA_EXE", str(base_prefix / "bin" / "conda"))

    assert create.first_writable_envs_dir(reject_active_envs_dir=True) == str(
        safe_envs_dir
    )
    assert (safe_envs_dir / ".conda_envs_dir_test").is_file()


@pytest.mark.parametrize(
    "function,raises",
    [
        ("create_application_entry_point", TypeError),
        ("ProgressFileWrapper", TypeError),
        ("create_fake_executable_softlink", TypeError),
        ("extract_tarball", TypeError),
    ],
)
def test_deprecations(function: str, raises: type[Exception] | None) -> None:
    raises_context = pytest.raises(raises) if raises else nullcontext()
    with pytest.deprecated_call(), raises_context:
        getattr(create, function)()
