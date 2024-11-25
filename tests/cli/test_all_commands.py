# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
This testing module is for tests which test multiple commands under the same
circumstance.
"""

import os

import pytest

from conda.auxlib.ish import dals
from conda.base.context import reset_context
from conda.exceptions import ChannelDenied
from conda.testing.fixtures import CondaCLIFixture, PathFactoryFixture

DENYLIST_CHANNEL = "denylist_channel_name"


@pytest.fixture(scope="function")
def denylist_valid_config(
    path_factory: PathFactoryFixture,
) -> None:
    reset_context(())
    path = path_factory(suffix=".yaml")
    path.write_text(
        dals(
            f"""
            denylist_channels:
              - {DENYLIST_CHANNEL}
            """
        )
    )

    os.environ["CONDARC"] = str(path)

    yield

    del os.environ["CONDARC"]


@pytest.fixture(scope="function")
def denylist_invalid_config(
    path_factory: PathFactoryFixture,
) -> None:
    reset_context(())
    path = path_factory(suffix=".yaml")
    path.write_text(
        dals(
            f"""
            channels:
              - {DENYLIST_CHANNEL}
            denylist_channels:
              - {DENYLIST_CHANNEL}
            """
        )
    )

    os.environ["CONDARC"] = str(path)

    yield

    del os.environ["CONDARC"]


@pytest.mark.parametrize(
    "command",
    (
        ("install", "--dry-run", "--channel", DENYLIST_CHANNEL, "python"),
        ("update", "--dry-run", "--all", "--channel", DENYLIST_CHANNEL),
        ("remove", "--dry-run", "--channel", DENYLIST_CHANNEL, "python"),
        (
            "create",
            "--dry-run",
            "--name",
            "test",
            "--channel",
            DENYLIST_CHANNEL,
            "python",
        ),
        ("search", "--channel", DENYLIST_CHANNEL, "python"),
    ),
)
def test_denylist_channels_from_options(
    conda_cli: CondaCLIFixture, command, denylist_valid_config
):
    """
    Ensure that the denylist_channels configuration option is respected.
    """
    with pytest.raises(ChannelDenied):
        conda_cli(*command)


@pytest.mark.parametrize(
    "command",
    (
        ("install", "--dry-run", "python"),
        (
            "update",
            "--dry-run",
            "--all",
        ),
        ("remove", "--dry-run", "python"),
        ("create", "--dry-run", "--name", "test", "python"),
        ("search", "python"),
    ),
)
def test_denylist_channels_from_config(
    conda_cli: CondaCLIFixture, command, denylist_invalid_config
):
    """
    Ensure when an invalid config file exists, that a ChannelDenied exception is raised.

    This can happen when a config file is created with a denylist channel that contradicts
    what is in the ``channels`` setting.
    """
    with pytest.raises(ChannelDenied):
        conda_cli(*command)
