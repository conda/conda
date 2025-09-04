# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
This testing module is for tests which test multiple commands under the same
circumstance.
"""

import pytest

from conda.exceptions import ChannelDenied
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
            ("env", "create", "--environment-specifier", "idontexist"),
            "error: argument --environment-specifier/--env-spec: invalid choice: 'idontexist'",
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
