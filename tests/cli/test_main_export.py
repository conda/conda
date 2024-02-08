# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os

import pytest
from pytest import MonkeyPatch

from conda.base.context import context, reset_context
from conda.exceptions import CondaValueError
from conda.testing import CondaCLIFixture


def test_export(conda_cli: CondaCLIFixture):
    env_name = "test_env"
    conda_cli("export", "-n", f"{env_name}", f"--file={env_name}.yml")
    assert os.path.exists(env_name + ".yml")


def test_export_override_channels(conda_cli: CondaCLIFixture, monkeypatch: MonkeyPatch):
    channels = (
        "tester",
        "defaults",
        "conda-forge",
    )
    monkeypatch.setenv("CONDA_CHANNELS", ",".join(channels))
    reset_context()
    assert context.channels == channels

    env_name = "test_env"
    conda_cli(
        "export",
        f"--name={env_name}",
        "--override-channels",
        "--channel=tester",
        f"--file={env_name}.yml",
    )
    assert os.path.exists(env_name + ".yml")

    with open(env_name + ".yml") as f:
        content = f.read()
        assert "tester" in content
        assert "conda-forge" not in content


def test_export_non_yaml(conda_cli: CondaCLIFixture):
    env_name = "test_env"
    with pytest.raises(
        CondaValueError, match="Export files must have a .yml or .yaml extension"
    ):
        conda_cli("export", f"--name={env_name}", f"--file={env_name}.txt")
