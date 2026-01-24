# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import sys
import warnings
from argparse import ArgumentParser, _StoreAction, _StoreTrueAction
from contextlib import nullcontext
from types import ModuleType
from typing import TYPE_CHECKING

import pytest

from conda.deprecations import DeprecatedError, DeprecationHandler

if TYPE_CHECKING:
    from packaging.version import Version
    from pytest_mock import MockerFixture

PENDING = pytest.param(
    DeprecationHandler("1.0"),  # deprecated
    PendingDeprecationWarning,  # warning
    "pending deprecation",  # message
    id="pending",
)
FUTURE = pytest.param(
    DeprecationHandler("2.0"),  # deprecated
    FutureWarning,  # warning
    "deprecated",  # message
    id="future",
)
DEPRECATED = pytest.param(
    DeprecationHandler("2.0"),  # deprecated
    DeprecationWarning,  # warning
    "deprecated",  # message
    id="deprecated",
)
REMOVE = pytest.param(
    DeprecationHandler("3.0"),  # deprecated
    None,  # warning
    None,  # message
    id="remove",
)

parametrize_user = pytest.mark.parametrize(
    "deprecated,warning,message",
    [PENDING, FUTURE, REMOVE],
)
parametrize_dev = pytest.mark.parametrize(
    "deprecated,warning,message",
    [PENDING, DEPRECATED, REMOVE],
)


@pytest.fixture
def module(mocker: MockerFixture) -> ModuleType:
    """Create a fresh module for testing deprecations in isolation."""
    module = ModuleType("test_deprecations_fresh")

    # Mock _get_module to return our fresh module
    mocker.patch(
        "conda.deprecations.DeprecationHandler._get_module",
        return_value=(module, module.__name__),
    )

    return module


@parametrize_dev
def test_function(
    deprecated: DeprecationHandler,
    warning: type[Warning] | None,
    message: str | None,
) -> None:
    """Calling a deprecated function displays associated warning (or error)."""
    with nullcontext() if warning else pytest.raises(DeprecatedError):

        @deprecated("2.0", "3.0")
        def foo():
            return True

        with pytest.warns(warning, match=message):
            assert foo()


@parametrize_dev
def test_method(
    deprecated: DeprecationHandler,
    warning: type[Warning] | None,
    message: str | None,
) -> None:
    """Calling a deprecated method displays associated warning (or error)."""
    with nullcontext() if warning else pytest.raises(DeprecatedError):

        class Bar:
            @deprecated("2.0", "3.0")
            def foo(self):
                return True

        with pytest.warns(warning, match=message):
            assert Bar().foo()


@parametrize_dev
def test_class(
    deprecated: DeprecationHandler,
    warning: type[Warning] | None,
    message: str | None,
) -> None:
    """Calling a deprecated class displays associated warning (or error)."""
    with nullcontext() if warning else pytest.raises(DeprecatedError):

        @deprecated("2.0", "3.0")
        class Foo:
            pass

        with pytest.warns(warning, match=message):
            assert Foo()


@parametrize_dev
def test_arguments(
    deprecated: DeprecationHandler,
    warning: type[Warning] | None,
    message: str | None,
) -> None:
    """Calling a deprecated argument displays associated warning (or error)."""
    with nullcontext() if warning else pytest.raises(DeprecatedError):

        @deprecated.argument("2.0", "3.0", "three")
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
    deprecated: DeprecationHandler,
    warning: type[Warning] | None,
    message: str | None,
) -> None:
    """Calling a deprecated argparse.Action displays associated warning (or error)."""
    with nullcontext() if warning else pytest.raises(DeprecatedError):
        parser = ArgumentParser()
        parser.add_argument(
            "--foo",
            action=deprecated.action("2.0", "3.0", _StoreTrueAction),
        )
        parser.add_argument(
            "bar",
            action=deprecated.action("2.0", "3.0", _StoreAction),
        )

        with pytest.warns(warning, match=message):
            parser.parse_args(["--foo", "some_value"])

        with pytest.warns(warning, match=message):
            parser.parse_args(["bar"])


@parametrize_dev
def test_module(
    deprecated: DeprecationHandler,
    warning: type[Warning] | None,
    message: str | None,
    module: ModuleType,  # mock calling module
) -> None:
    """Importing a deprecated module displays associated warning (or error)."""
    with (
        pytest.warns(warning, match=message)
        if warning
        else pytest.raises(DeprecatedError)
    ):
        deprecated.module("2.0", "3.0")


@parametrize_dev
def test_constant(
    deprecated: DeprecationHandler,
    warning: type[Warning] | None,
    message: str | None,
    module: ModuleType,
) -> None:
    """Using a deprecated constant displays associated warning (or error)."""
    with nullcontext() if warning else pytest.raises(DeprecatedError):
        deprecated.constant("2.0", "3.0", "SOME_CONSTANT", 42)

        with pytest.warns(warning, match=message):
            module.SOME_CONSTANT


def test_constant_multiple_same_module(module: ModuleType) -> None:
    """Multiple deprecated constants in the same module all report correct source location.

    Regression test for #15623.
    """
    deprecated = DeprecationHandler("2.0")

    # Deprecate multiple constants in the same module
    deprecated.constant("2.0", "3.0", "CONST_A", "value_a")
    deprecated.constant("2.0", "3.0", "CONST_B", "value_b")
    deprecated.constant("2.0", "3.0", "CONST_C", "value_c")

    # Each access should warn with correct source location (this file, not deprecations.py)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        module.CONST_A
        assert len(w) == 1
        assert w[0].filename == __file__

        module.CONST_B
        assert len(w) == 2
        assert w[1].filename == __file__

        module.CONST_C
        assert len(w) == 3
        assert w[2].filename == __file__


@parametrize_dev
def test_topic(
    deprecated: DeprecationHandler,
    warning: type[Warning] | None,
    message: str | None,
) -> None:
    """Reaching a deprecated topic displays associated warning (or error)."""
    with (
        pytest.warns(warning, match=message)
        if warning
        else pytest.raises(DeprecatedError)
    ):
        deprecated.topic("2.0", "3.0", topic="Some special topic")


def test_get_module() -> None:
    """Test that _get_module correctly identifies the calling module."""
    deprecated = DeprecationHandler("2.0")

    # Wrapper simulates real-world usage where _get_module is called from
    # within a deprecation method (e.g., constant, module, topic)
    def wrapper():
        return deprecated._get_module(0)

    module, fullname = wrapper()
    assert module is sys.modules[__name__]
    assert fullname == __name__


def test_version_fallback() -> None:
    """Test that conda can run even if deprecations can't parse the version."""
    deprecated = DeprecationHandler(None)  # type: ignore[arg-type]
    assert deprecated._version_less_than("0")
    assert deprecated._version_tuple is None
    version: Version = deprecated._version_object  # type: ignore[assignment]
    assert version.major == version.minor == version.micro == 0
