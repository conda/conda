# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest

from conda import CondaError, plugins
from conda.exception_handler import ExceptionHandler
from conda.exceptions import PackagesNotFoundError
from conda.plugins.types import CondaExceptionHandler

if TYPE_CHECKING:
    from conda.plugins.types import CondaExceptionInfo


class CatchAllPlugin:
    """Records every CondaError it sees."""

    def __init__(self):
        self.calls: list[CondaExceptionInfo] = []

    @plugins.hookimpl
    def conda_exception_handlers(self):
        yield CondaExceptionHandler(
            name="catch-all",
            hook=self.calls.append,
            run_for={"CondaError"},
        )


class PackagesOnlyPlugin:
    """Only fires for PackagesNotFoundError (and subclasses via MRO)."""

    def __init__(self):
        self.calls: list[CondaExceptionInfo] = []

    @plugins.hookimpl
    def conda_exception_handlers(self):
        yield CondaExceptionHandler(
            name="packages-only",
            hook=self.calls.append,
            run_for={"PackagesNotFoundError"},
        )


class ExplodingPlugin:
    """Raises inside its hook."""

    raised = False

    @plugins.hookimpl
    def conda_exception_handlers(self):
        def _boom(exc_info: CondaExceptionInfo) -> None:
            ExplodingPlugin.raised = True
            raise RuntimeError("plugin bug")

        yield CondaExceptionHandler(
            name="exploding",
            hook=_boom,
            run_for={"CondaError"},
        )


class SystemExitPlugin:
    """Raises SystemExit inside its hook."""

    @plugins.hookimpl
    def conda_exception_handlers(self):
        def _exit(exc_info: CondaExceptionInfo) -> None:
            raise SystemExit(42)

        yield CondaExceptionHandler(
            name="system-exit",
            hook=_exit,
            run_for={"CondaError"},
        )


@pytest.fixture()
def catch_all_plugin(plugin_manager):
    p = CatchAllPlugin()
    plugin_manager.register(p)
    return p


@pytest.fixture()
def packages_only_plugin(plugin_manager):
    p = PackagesOnlyPlugin()
    plugin_manager.register(p)
    return p


@pytest.fixture()
def exploding_plugin(plugin_manager):
    ExplodingPlugin.raised = False
    p = ExplodingPlugin()
    plugin_manager.register(p)
    return p


@pytest.fixture()
def system_exit_plugin(plugin_manager):
    p = SystemExitPlugin()
    plugin_manager.register(p)
    return p


def test_catch_all_receives_conda_error(catch_all_plugin, plugin_manager):
    """A handler registered for CondaError is invoked for any CondaError."""
    exc = CondaError("boom")
    try:
        raise exc
    except CondaError:
        _, exc_val, exc_tb = sys.exc_info()
        plugin_manager.invoke_exception_handlers(exc_val, exc_tb)

    assert len(catch_all_plugin.calls) == 1
    info = catch_all_plugin.calls[0]
    assert info.exc_value is exc
    assert info.exc_type is CondaError
    assert info.exc_traceback is not None
    assert isinstance(info.argv, tuple)
    assert isinstance(info.conda_version, str)
    assert info.return_code == 1


def test_catch_all_receives_active_prefix(catch_all_plugin, plugin_manager):
    """active_prefix is populated from context."""
    exc = CondaError("boom")
    try:
        raise exc
    except CondaError:
        _, exc_val, exc_tb = sys.exc_info()
        plugin_manager.invoke_exception_handlers(exc_val, exc_tb)

    info = catch_all_plugin.calls[0]
    assert isinstance(info.active_prefix, (str, type(None)))


def test_run_for_filters_by_class_name(
    catch_all_plugin, packages_only_plugin, plugin_manager
):
    """A handler with run_for={'PackagesNotFoundError'} does not fire for plain CondaError."""
    try:
        raise CondaError("generic")
    except CondaError:
        _, exc_val, exc_tb = sys.exc_info()
        plugin_manager.invoke_exception_handlers(exc_val, exc_tb)

    assert len(catch_all_plugin.calls) == 1
    assert len(packages_only_plugin.calls) == 0


def test_run_for_matches_subclasses_via_mro(packages_only_plugin, plugin_manager):
    """run_for matches against the full MRO, so PackagesNotFoundError catches subclasses."""
    exc = PackagesNotFoundError(["numpy"])
    try:
        raise exc
    except CondaError:
        _, exc_val, exc_tb = sys.exc_info()
        plugin_manager.invoke_exception_handlers(exc_val, exc_tb)

    assert len(packages_only_plugin.calls) == 1
    assert packages_only_plugin.calls[0].exc_value is exc


def test_non_conda_error_skipped(catch_all_plugin, plugin_manager):
    """Non-CondaError exceptions are not dispatched to handlers."""
    try:
        raise ValueError("not a conda error")
    except ValueError:
        _, exc_val, exc_tb = sys.exc_info()
        plugin_manager.invoke_exception_handlers(exc_val, exc_tb)

    assert len(catch_all_plugin.calls) == 0


def test_handler_exception_swallowed(exploding_plugin, catch_all_plugin, plugin_manager):
    """A handler that raises does not break the invocation of subsequent handlers."""
    try:
        raise CondaError("test")
    except CondaError:
        _, exc_val, exc_tb = sys.exc_info()
        plugin_manager.invoke_exception_handlers(exc_val, exc_tb)

    assert ExplodingPlugin.raised
    assert len(catch_all_plugin.calls) == 1


def test_system_exit_in_handler_swallowed(system_exit_plugin, plugin_manager):
    """A handler raising SystemExit cannot kill conda's error path."""
    try:
        raise CondaError("test")
    except CondaError:
        _, exc_val, exc_tb = sys.exc_info()
        plugin_manager.invoke_exception_handlers(exc_val, exc_tb)


def test_exception_info_is_frozen(catch_all_plugin, plugin_manager):
    """CondaExceptionInfo is a frozen dataclass -- attributes cannot be mutated."""
    try:
        raise CondaError("test")
    except CondaError:
        _, exc_val, exc_tb = sys.exc_info()
        plugin_manager.invoke_exception_handlers(exc_val, exc_tb)

    info = catch_all_plugin.calls[0]
    with pytest.raises(AttributeError):
        info.return_code = 99


def test_invoked_via_exception_handler_class(catch_all_plugin, plugin_manager):
    """ExceptionHandler.handle_exception invokes exception handler plugins."""
    handler = ExceptionHandler()
    exc = CondaError("integration test")
    try:
        raise exc
    except CondaError:
        _, exc_val, exc_tb = sys.exc_info()
        handler.handle_exception(exc_val, exc_tb)

    assert len(catch_all_plugin.calls) == 1
    assert catch_all_plugin.calls[0].exc_value is exc


def test_no_handlers_registered(plugin_manager):
    """Invocation is a no-op when no handlers are registered."""
    try:
        raise CondaError("test")
    except CondaError:
        _, exc_val, exc_tb = sys.exc_info()
        plugin_manager.invoke_exception_handlers(exc_val, exc_tb)
