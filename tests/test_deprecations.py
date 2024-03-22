# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import sys
from argparse import ArgumentParser, _StoreTrueAction
from contextlib import nullcontext
from typing import TYPE_CHECKING

import pytest

from conda.deprecations import DeprecatedError, DeprecationHandler

if TYPE_CHECKING:
    from packaging.version import Version

    from conda.deprecations import DevDeprecationType, UserDeprecationType

PENDING = pytest.param("1.0", PendingDeprecationWarning, "pending", id="pending")
FUTURE = pytest.param("2.0", FutureWarning, "deprecated", id="future")
DEPRECATED = pytest.param("2.0", DeprecationWarning, "deprecated", id="deprecated")
REMOVE = pytest.param("3.0", None, None, id="remove")

parametrize_user = pytest.mark.parametrize(
    "version,warning,message",
    [PENDING, FUTURE, REMOVE],
)
parametrize_dev = pytest.mark.parametrize(
    "version,warning,message",
    [PENDING, DEPRECATED, REMOVE],
)


@parametrize_dev
def test_function(
    version: str,
    warning: DevDeprecationType | None,
    message: str | None,
) -> None:
    """Calling a deprecated function displays associated warning (or error)."""
    with nullcontext() if warning else pytest.raises(DeprecatedError):

        @DeprecationHandler(version)("2.0", "3.0")
        def foo():
            return True

        with pytest.warns(warning, match=message):
            assert foo()


@parametrize_dev
def test_method(
    version: str,
    warning: DevDeprecationType | None,
    message: str | None,
) -> None:
    """Calling a deprecated method displays associated warning (or error)."""
    with nullcontext() if warning else pytest.raises(DeprecatedError):

        class Bar:
            @DeprecationHandler(version)("2.0", "3.0")
            def foo(self):
                return True

        with pytest.warns(warning, match=message):
            assert Bar().foo()


@parametrize_dev
def test_class(
    version: str,
    warning: DevDeprecationType | None,
    message: str | None,
) -> None:
    """Calling a deprecated class displays associated warning (or error)."""
    with nullcontext() if warning else pytest.raises(DeprecatedError):

        @DeprecationHandler(version)("2.0", "3.0")
        class Foo:
            pass

        with pytest.warns(warning, match=message):
            assert Foo()


@parametrize_dev
def test_arguments(
    version: str,
    warning: DevDeprecationType | None,
    message: str | None,
) -> None:
    """Calling a deprecated argument displays associated warning (or error)."""
    with nullcontext() if warning else pytest.raises(DeprecatedError):

        @DeprecationHandler(version).argument("2.0", "3.0", "three")
        def foo(one, two):
            return True

        # too many arguments, can only deprecate keyword arguments
        with pytest.raises(TypeError):
            assert foo(1, 2, 3)

        # alerting user to pending deprecation
        with pytest.warns(warning, match=message):
            assert foo(1, 2, three=3)

        # normal usage not needing deprecation
        assert foo(1, 2)


@parametrize_user
def test_action(
    version: str,
    warning: UserDeprecationType | None,
    message: str | None,
) -> None:
    """Calling a deprecated argparse.Action displays associated warning (or error)."""
    with nullcontext() if warning else pytest.raises(DeprecatedError):
        parser = ArgumentParser()
        parser.add_argument(
            "--foo",
            action=DeprecationHandler(version).action("2.0", "3.0", _StoreTrueAction),
        )

        with pytest.warns(warning, match=message):
            parser.parse_args(["--foo"])


@parametrize_dev
def test_module(
    version: str,
    warning: DevDeprecationType | None,
    message: str | None,
) -> None:
    """Importing a deprecated module displays associated warning (or error)."""
    with nullcontext() if warning else pytest.raises(DeprecatedError):
        with pytest.warns(warning, match=message):
            DeprecationHandler(version).module("2.0", "3.0")


@parametrize_dev
def test_constant(
    version: str,
    warning: DevDeprecationType | None,
    message: str | None,
) -> None:
    """Using a deprecated constant displays associated warning (or error)."""
    with nullcontext() if warning else pytest.raises(DeprecatedError):
        DeprecationHandler(version).constant("2.0", "3.0", "SOME_CONSTANT", 42)
        module = sys.modules[__name__]

        with pytest.warns(warning, match=message):
            module.SOME_CONSTANT


@parametrize_dev
def test_topic(
    version: str,
    warning: DevDeprecationType | None,
    message: str | None,
) -> None:
    """Reaching a deprecated topic displays associated warning (or error)."""
    with nullcontext() if warning else pytest.raises(DeprecatedError):
        with pytest.warns(warning, match=message):
            DeprecationHandler(version).topic("2.0", "3.0", topic="Some special topic")


def test_version_fallback() -> None:
    """Test that conda can run even if deprecations can't parse the version."""
    deprecated = DeprecationHandler(None)  # type: ignore[arg-type]
    assert deprecated._version_less_than("0")
    assert deprecated._version_tuple is None
    version: Version = deprecated._version_object  # type: ignore[assignment]
    assert version.major == version.minor == version.micro == 0
