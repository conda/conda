# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
This testing module is for tests which test multiple commands under the same
circumstance.
"""

from __future__ import annotations

import re
import warnings
from argparse import ArgumentParser
from typing import TYPE_CHECKING

import pytest

from conda.cli.helpers import add_parser_environment_specifier
from conda.exceptions import ChannelDenied

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from conda.testing.fixtures import CondaCLIFixture

DENYLIST_CHANNEL: str = "denylist_channel_name"
DENYLIST_CHANNEL_URL: str = "https://conda.anaconda.org/denylist_channel_name"


@pytest.mark.parametrize(
    "command",
    (
        ("install", "--dry-run", "python"),
        ("update", "--dry-run", "--all"),
        ("remove", "--dry-run", "python"),
        ("create", "--dry-run", "python"),
        ("search", "python"),
    ),
)
@pytest.mark.parametrize("from_options", [True, False])
@pytest.mark.parametrize("denylist_channel", [DENYLIST_CHANNEL, DENYLIST_CHANNEL_URL])
def test_denylist_channels(
    monkeypatch: pytest.MonkeyPatch,
    conda_cli: CondaCLIFixture,
    command: tuple[str, ...],
    from_options: bool,
    denylist_channel: str,
):
    """
    Ensures that the ``denylist_channels`` configuration option is respected when
    passed in via the command line or an environment variable.
    """
    monkeypatch.setenv("CONDA_DENYLIST_CHANNELS", denylist_channel)
    if from_options:
        command = (*command, f"--channel={denylist_channel}")
    else:
        monkeypatch.setenv("CONDA_CHANNEL", denylist_channel)
    with pytest.raises(ChannelDenied):
        conda_cli(*command)


@pytest.mark.parametrize(
    ("command", "err_message"),
    (
        (
            ("env", "create", "--format", "idontexist"),
            "error: argument --format: invalid choice: 'idontexist'",
        ),
        (
            ("install", "--solver", "idontexist"),
            "error: argument --solver: invalid choice: 'idontexist'",
        ),
    ),
)
def test_commands_with_plugin_backed_options(
    conda_cli: CondaCLIFixture,
    command: tuple[str, ...],
    err_message: str,
    capsys,
):
    """Ensure that conda raises an error when a plugin-backed option
    is used with an invalid value.
    """
    with pytest.raises(SystemExit):
        conda_cli(*command)
    captured = capsys.readouterr()
    assert err_message in captured.err


@pytest.mark.parametrize(
    "flag",
    ["--environment-specifier", "--env-spec"],
)
def test_env_spec_deprecation(mocker: MockerFixture, flag: str) -> None:
    # Provide a known valid choice so LazyChoicesAction does not reject it.
    specifier = "yaml"
    mocker.patch(
        "conda.base.context.context.plugin_manager.get_environment_specifiers",
        return_value=[specifier],
    )

    parser = ArgumentParser()
    add_parser_environment_specifier(parser)

    with pytest.deprecated_call():
        parser.parse_args([flag, specifier])

    # no deprecation warning when unused
    with warnings.catch_warnings():
        warnings.simplefilter("error", FutureWarning)
        parser.parse_args(["--format", specifier])


@pytest.mark.parametrize(
    "command",
    ["activate", "deactivate"],
)
def test_activate_help_commands_exit_0_rc(
    conda_cli: CondaCLIFixture,
    command: str,
):
    """Ensure that conda returns a 0 error code when cli --help is called"""
    stdout, stderr, rc = conda_cli(command, "-h", raises=SystemExit)
    assert rc == 0, f"conda {command} failed ({rc}): {stderr}"
    assert f"usage: conda {command}" in stdout
    assert not re.search(r"\berror\b", stdout, re.IGNORECASE)
    assert not re.search(r"\berror\b", stderr, re.IGNORECASE)
