# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os

import pytest
from pytest import MonkeyPatch

from conda.base.context import context, reset_context
from conda.exceptions import CondaValueError
from conda.testing import CondaCLIFixture

TEST_ENV_NAME = "test_env"


def test_export(conda_cli: CondaCLIFixture):
    conda_cli("export", "-n", f"{TEST_ENV_NAME}", f"--file={TEST_ENV_NAME}.yml")
    assert os.path.exists(TEST_ENV_NAME + ".yml")

    # check bare minimum contents of the export file
    with open(TEST_ENV_NAME + ".yml") as f:
        content = f.read()
        assert "name: " + TEST_ENV_NAME in content


def test_export_override_channels(conda_cli: CondaCLIFixture, monkeypatch: MonkeyPatch):
    channels = (
        "tester",
        "defaults",
        "conda-forge",
    )
    monkeypatch.setenv("CONDA_CHANNELS", ",".join(channels))
    reset_context()
    assert set(channels) <= set(context.channels)

    conda_cli(
        "export",
        f"--name={TEST_ENV_NAME}",
        "--override-channels",
        "--channel=tester",
        f"--file={TEST_ENV_NAME}.yml",
    )
    assert os.path.exists(TEST_ENV_NAME + ".yml")

    with open(TEST_ENV_NAME + ".yml") as f:
        content = f.read()
        assert "tester" in content
        assert "conda-forge" not in content


def test_export_add_channels(conda_cli: CondaCLIFixture):
    conda_cli(
        "export",
        f"--name={TEST_ENV_NAME}",
        "--channel=include-me",
        f"--file={TEST_ENV_NAME}.yml",
    )

    with open(TEST_ENV_NAME + ".yml") as f:
        content = f.read()
        assert "include-me" in content


def test_export_yaml_file_extension(conda_cli: CondaCLIFixture):
    with pytest.raises(
        CondaValueError,
        match="Export files must have a valid extension \\('.yml', '.yaml'\\)",
    ):
        conda_cli("export", f"--name={TEST_ENV_NAME}", f"--file={TEST_ENV_NAME}.txt")


def test_execute_export_no_file_specified(conda_cli: CondaCLIFixture):
    env_name = "no-file-test"
    conda_cli("export", f"--name={env_name}")
    assert not os.path.exists("env_name" + ".yml")
