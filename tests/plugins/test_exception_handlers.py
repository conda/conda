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


class BaseExceptionPlugin:
    """Records every exception regardless of type."""

    def __init__(self):
        self.calls: list[CondaExceptionInfo] = []

    @plugins.hookimpl
    def conda_exception_handlers(self):
        yield CondaExceptionHandler(
            name="base-exception",
            hook=self.calls.append,
            run_for={"BaseException"},
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
def base_exception_plugin(plugin_manager):
    p = BaseExceptionPlugin()
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


def test_non_conda_error_not_matched_by_conda_handler(catch_all_plugin, plugin_manager):
    """A ValueError is dispatched but not matched by a handler with run_for={'CondaError'}."""
    try:
        raise ValueError("not a conda error")
    except ValueError:
        _, exc_val, exc_tb = sys.exc_info()
        plugin_manager.invoke_exception_handlers(exc_val, exc_tb)

    assert len(catch_all_plugin.calls) == 0


def test_handler_exception_swallowed(
    exploding_plugin, catch_all_plugin, plugin_manager
):
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


def test_base_exception_plugin_receives_value_error(
    base_exception_plugin, plugin_manager
):
    """A handler with run_for={'BaseException'} fires for any exception type."""
    exc = ValueError("oops")
    try:
        raise exc
    except ValueError:
        _, exc_val, exc_tb = sys.exc_info()
        plugin_manager.invoke_exception_handlers(exc_val, exc_tb)

    assert len(base_exception_plugin.calls) == 1
    info = base_exception_plugin.calls[0]
    assert info.exc_value is exc
    assert info.exc_type is ValueError


def test_memory_error_dispatched(base_exception_plugin, plugin_manager):
    """MemoryError is dispatched to handlers registered for BaseException."""
    exc = MemoryError()
    try:
        raise exc
    except MemoryError:
        _, exc_val, exc_tb = sys.exc_info()
        plugin_manager.invoke_exception_handlers(exc_val, exc_tb)

    assert len(base_exception_plugin.calls) == 1
    info = base_exception_plugin.calls[0]
    assert info.exc_value is exc
    assert info.exc_type is MemoryError


def test_keyboard_interrupt_dispatched(base_exception_plugin, plugin_manager):
    """KeyboardInterrupt is dispatched to handlers registered for BaseException."""
    exc = KeyboardInterrupt()
    try:
        raise exc
    except KeyboardInterrupt:
        _, exc_val, exc_tb = sys.exc_info()
        plugin_manager.invoke_exception_handlers(exc_val, exc_tb)

    assert len(base_exception_plugin.calls) == 1
    info = base_exception_plugin.calls[0]
    assert info.exc_value is exc
    assert info.exc_type is KeyboardInterrupt


def test_system_exit_dispatched(base_exception_plugin, plugin_manager):
    """SystemExit is dispatched to handlers registered for BaseException."""
    exc = SystemExit(2)
    try:
        raise exc
    except SystemExit:
        _, exc_val, exc_tb = sys.exc_info()
        plugin_manager.invoke_exception_handlers(exc_val, exc_tb)

    assert len(base_exception_plugin.calls) == 1
    info = base_exception_plugin.calls[0]
    assert info.exc_value is exc
    assert info.exc_type is SystemExit
    assert info.return_code == 2


def test_system_exit_return_code_from_code_attr(base_exception_plugin, plugin_manager):
    """SystemExit.code is used as the return_code."""
    exc = SystemExit(42)
    try:
        raise exc
    except SystemExit:
        _, exc_val, exc_tb = sys.exc_info()
        plugin_manager.invoke_exception_handlers(exc_val, exc_tb)

    info = base_exception_plugin.calls[0]
    assert info.return_code == 42


def test_conda_error_not_matched_by_memory_error_handler(plugin_manager):
    """A handler with run_for={'MemoryError'} does not fire for CondaError."""

    class MemoryErrorPlugin:
        def __init__(self):
            self.calls: list[CondaExceptionInfo] = []

        @plugins.hookimpl
        def conda_exception_handlers(self):
            yield CondaExceptionHandler(
                name="memory-only",
                hook=self.calls.append,
                run_for={"MemoryError"},
            )

    p = MemoryErrorPlugin()
    plugin_manager.register(p)

    try:
        raise CondaError("test")
    except CondaError:
        _, exc_val, exc_tb = sys.exc_info()
        plugin_manager.invoke_exception_handlers(exc_val, exc_tb)

    assert len(p.calls) == 0


def test_combined_run_for_scopes(plugin_manager):
    """A handler with run_for={'CondaError', 'MemoryError'} fires for both types."""

    class CombinedPlugin:
        def __init__(self):
            self.calls: list[CondaExceptionInfo] = []

        @plugins.hookimpl
        def conda_exception_handlers(self):
            yield CondaExceptionHandler(
                name="combined",
                hook=self.calls.append,
                run_for={"CondaError", "MemoryError"},
            )

    p = CombinedPlugin()
    plugin_manager.register(p)

    try:
        raise CondaError("test")
    except CondaError:
        _, exc_val, exc_tb = sys.exc_info()
        plugin_manager.invoke_exception_handlers(exc_val, exc_tb)

    try:
        raise MemoryError()
    except MemoryError:
        _, exc_val, exc_tb = sys.exc_info()
        plugin_manager.invoke_exception_handlers(exc_val, exc_tb)

    assert len(p.calls) == 2
    assert p.calls[0].exc_type is CondaError
    assert p.calls[1].exc_type is MemoryError
