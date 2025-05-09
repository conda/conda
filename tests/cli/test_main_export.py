# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest

from conda.base.context import context, reset_context
from conda.common.serialize import json_load, yaml_safe_load
from conda.exceptions import CondaValueError

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import MonkeyPatch

    from conda.testing.fixtures import CondaCLIFixture, PathFactory


def test_export(conda_cli: CondaCLIFixture, path_factory: PathFactory) -> None:
    name = uuid.uuid4().hex
    path = path_factory(suffix=".yml")
    conda_cli("export", f"--name={name}", f"--file={path}")
    assert path.exists()

    # check bare minimum contents of the export file
    data = yaml_safe_load(path.read_text())
    assert data["name"] == name


def test_export_override_channels(
    conda_cli: CondaCLIFixture,
    monkeypatch: MonkeyPatch,
    path_factory: PathFactory,
) -> None:
    # channels to be ignored
    channels = (uuid.uuid4().hex, uuid.uuid4().hex)
    monkeypatch.setenv("CONDA_CHANNELS", ",".join(channels))
    reset_context()
    assert set(channels) <= set(context.channels)

    name = uuid.uuid4().hex
    path = path_factory(suffix=".yml")
    conda_cli(
        "export",
        f"--name={name}",
        "--override-channels",
        "--channel=tester",
        f"--file={path}",
    )
    assert path.exists()

    data = yaml_safe_load(path.read_text())
    assert data["channels"] == ["tester"]


def test_export_add_channels(
    conda_cli: CondaCLIFixture,
    path_factory: PathFactory,
) -> None:
    name = uuid.uuid4().hex
    path = path_factory(suffix=".yml")
    conda_cli(
        "export",
        f"--name={name}",
        "--channel=include-me",
        f"--file={path}",
    )
    assert path.exists()

    data = yaml_safe_load(path.read_text())
    assert data["channels"] == ["include-me", *context.channels]


def test_export_yaml_file_extension(
    conda_cli: CondaCLIFixture,
    path_factory: PathFactory,
) -> None:
    name = uuid.uuid4().hex
    path = path_factory(suffix=".txt")
    with pytest.raises(
        CondaValueError,
        match=r"Export files must have a valid extension \('.yml', '.yaml'\)",
    ):
        conda_cli("export", f"--name={name}", f"--file={path}")


def test_execute_export_no_file_specified(
    conda_cli: CondaCLIFixture,
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)

    # ensure current directory is empty
    assert not list(tmp_path.iterdir())

    name = uuid.uuid4().hex
    conda_cli("export", f"--name={name}")

    # ensure no environment file was created
    assert not list(tmp_path.iterdir())


def test_export_with_json(
    conda_cli: CondaCLIFixture,
    path_factory: PathFactory,
) -> None:
    name = uuid.uuid4().hex
    path = path_factory(suffix=".yml")
    stdout, stderr, code = conda_cli(
        "export",
        f"--name={name}",
        "--json",
        f"--file={path}",
    )
    assert stdout
    assert not stderr
    assert not code

    data = json_load(stdout)
    assert data["name"] == name

    assert path.exists()
    assert yaml_safe_load(path.read_text()) == data
