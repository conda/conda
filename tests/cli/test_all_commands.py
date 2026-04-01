# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
This testing module is for tests which test multiple commands under the same
circumstance.
"""

from __future__ import annotations

import warnings
from argparse import ArgumentParser
from typing import TYPE_CHECKING

import pytest

from conda.cli.helpers import add_parser_environment_specifier
from conda.deprecations import DeprecatedError, DeprecationHandler
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


_FAKE_SPECIFIER = "yaml"
"""
A fake environment-specifier plugin name used as a valid choice in tests.
"""

_ENV_SPEC_FLAGS = pytest.mark.parametrize(
    "flag", ["--environment-specifier", "--env-spec"]
)
"""
Parametrize over both flag aliases so both are covered.
"""


def _make_parser(mocker: MockerFixture, handler: DeprecationHandler) -> ArgumentParser:
    """Return a fresh ArgumentParser with the environment-specifier arguments
    registered, using the given *handler* as the ``deprecated`` singleton and
    a single fake specifier choice so validation passes.

    TODO: Remove test before 26.9.0 release
    """
    # Replace the module-level `deprecated` object so the action is built with
    # the version embedded in *handler* rather than the real conda version.
    mocker.patch("conda.cli.helpers.deprecated", handler)

    # Provide a known valid choice so LazyChoicesAction does not reject it.
    mocker.patch(
        "conda.base.context.context.plugin_manager.get_environment_specifiers",
        return_value=[_FAKE_SPECIFIER],
    )

    parser = ArgumentParser()
    add_parser_environment_specifier(parser)
    return parser


@_ENV_SPEC_FLAGS
def test_env_spec_deprecation_pending(mocker: MockerFixture, flag: str) -> None:
    """
    Before 26.5 the flag emits a ``PendingDeprecationWarning``.

    TODO: Remove test before 26.9.0 release
    """
    parser = _make_parser(mocker, DeprecationHandler("26.3"))

    with pytest.warns(PendingDeprecationWarning, match="pending deprecation"):
        parser.parse_args([flag, _FAKE_SPECIFIER])


@_ENV_SPEC_FLAGS
def test_env_spec_deprecation_active(mocker: MockerFixture, flag: str) -> None:
    """
    From 26.5 onwards the flag emits a ``FutureWarning`` (active deprecation).

    TODO: Remove test before 26.9.0 release
    """
    parser = _make_parser(mocker, DeprecationHandler("26.5"))

    with pytest.warns(FutureWarning, match="deprecated"):
        parser.parse_args([flag, _FAKE_SPECIFIER])


def test_env_spec_deprecation_removal(mocker: MockerFixture) -> None:
    """
    At 26.9 the option should no longer exist: building the parser raises
    ``DeprecatedError`` to alert developers that the dead code must be removed.

    TODO: Remove test before 26.9.0 release
    """
    mocker.patch("conda.cli.helpers.deprecated", DeprecationHandler("26.9"))
    mocker.patch(
        "conda.base.context.context.plugin_manager.get_environment_specifiers",
        return_value=[_FAKE_SPECIFIER],
    )

    parser = ArgumentParser()
    with pytest.raises(DeprecatedError):
        add_parser_environment_specifier(parser)


def test_env_spec_no_warning_when_not_used(mocker: MockerFixture) -> None:
    """
    Passing ``--format`` (the replacement flag) must not trigger any
    deprecation warning, even when the deprecated handler is at the active
    version.

    TODO: Remove before 26.9.0 release
    """
    parser = _make_parser(mocker, DeprecationHandler("26.5"))

    # pytest.warns(None) would raise in newer pytest when *no* warning fires;
    # use warnings.catch_warnings to assert silence instead.
    with warnings.catch_warnings():
        warnings.simplefilter("error", FutureWarning)
        # --format stores into the same dest; should not raise
        parser.parse_args(["--format", _FAKE_SPECIFIER])
