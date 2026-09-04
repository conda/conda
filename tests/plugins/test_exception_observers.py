# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest

from conda import CondaError, plugins
from conda import __version__ as CONDA_VERSION
from conda.exception_handler import ExceptionHandler
from conda.exceptions import PackagesNotFoundError
from conda.plugins.types import CondaExceptionObserver

if TYPE_CHECKING:
    from conda.plugins.types import CondaExceptionEvent


class CatchAllPlugin:
    """Records every CondaError it sees."""

    def __init__(self):
        self.calls: list[CondaExceptionEvent] = []

    @plugins.hookimpl
    def conda_exception_observers(self):
        yield CondaExceptionObserver(
            name="catch-all",
            hook=self.calls.append,
            watch_for={"CondaError"},
        )


class BaseExceptionPlugin:
    """Records every exception regardless of type."""

    def __init__(self):
        self.calls: list[CondaExceptionEvent] = []

    @plugins.hookimpl
    def conda_exception_observers(self):
        yield CondaExceptionObserver(
            name="base-exception",
            hook=self.calls.append,
            watch_for={"BaseException"},
        )


class PackagesOnlyPlugin:
    """Only fires for PackagesNotFoundError (and subclasses via MRO)."""

    def __init__(self):
        self.calls: list[CondaExceptionEvent] = []

    @plugins.hookimpl
    def conda_exception_observers(self):
        yield CondaExceptionObserver(
            name="packages-only",
            hook=self.calls.append,
            watch_for={"PackagesNotFoundError"},
        )


class ExplodingPlugin:
    """Raises inside its hook."""

    raised = False

    @plugins.hookimpl
    def conda_exception_observers(self):
        def _boom(exc_info: CondaExceptionEvent) -> None:
            ExplodingPlugin.raised = True
            raise RuntimeError("plugin bug")

        yield CondaExceptionObserver(
            name="exploding",
            hook=_boom,
            watch_for={"CondaError"},
        )


class SystemExitPlugin:
    """Raises SystemExit inside its hook."""

    @plugins.hookimpl
    def conda_exception_observers(self):
        def _exit(exc_info: CondaExceptionEvent) -> None:
            raise SystemExit(42)

        yield CondaExceptionObserver(
            name="system-exit",
            hook=_exit,
            watch_for={"CondaError"},
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
    """An observer registered for CondaError is invoked for any CondaError."""
    exc = CondaError("boom")
    try:
        raise exc
    except CondaError:
        _, exc_val, exc_tb = sys.exc_info()
        plugin_manager.invoke_exception_observers(exc_val, exc_tb)

    assert len(catch_all_plugin.calls) == 1
    info = catch_all_plugin.calls[0]
    assert info.exc_value is exc
    assert info.exc_type is CondaError
    assert info.exc_traceback is not None
    assert isinstance(info.argv, tuple)
    assert info.conda_version == CONDA_VERSION
    assert info.return_code == 1


def test_catch_all_receives_active_prefix(catch_all_plugin, plugin_manager):
    """active_prefix is populated from context."""
    exc = CondaError("boom")
    try:
        raise exc
    except CondaError:
        _, exc_val, exc_tb = sys.exc_info()
        plugin_manager.invoke_exception_observers(exc_val, exc_tb)

    from conda.base.context import context

    info = catch_all_plugin.calls[0]
    assert info.active_prefix == context.active_prefix


def test_watch_for_filters_by_class_name(
    catch_all_plugin, packages_only_plugin, plugin_manager
):
    """An observer with watch_for={'PackagesNotFoundError'} does not fire for plain CondaError."""
    try:
        raise CondaError("generic")
    except CondaError:
        _, exc_val, exc_tb = sys.exc_info()
        plugin_manager.invoke_exception_observers(exc_val, exc_tb)

    assert len(catch_all_plugin.calls) == 1
    assert len(packages_only_plugin.calls) == 0


def test_watch_for_matches_subclasses_via_mro(packages_only_plugin, plugin_manager):
    """watch_for matches against the full MRO, so PackagesNotFoundError catches subclasses."""
    exc = PackagesNotFoundError(["numpy"])
    try:
        raise exc
    except CondaError:
        _, exc_val, exc_tb = sys.exc_info()
        plugin_manager.invoke_exception_observers(exc_val, exc_tb)

    assert len(packages_only_plugin.calls) == 1
    assert packages_only_plugin.calls[0].exc_value is exc


def test_non_conda_error_not_matched_by_conda_handler(catch_all_plugin, plugin_manager):
    """A ValueError is dispatched but not matched by an observer with watch_for={'CondaError'}."""
    try:
        raise ValueError("not a conda error")
    except ValueError:
        _, exc_val, exc_tb = sys.exc_info()
        plugin_manager.invoke_exception_observers(exc_val, exc_tb)

    assert len(catch_all_plugin.calls) == 0


def test_observer_exception_swallowed(
    exploding_plugin, catch_all_plugin, plugin_manager
):
    """An observer that raises does not break the invocation of subsequent observers."""
    try:
        raise CondaError("test")
    except CondaError:
        _, exc_val, exc_tb = sys.exc_info()
        plugin_manager.invoke_exception_observers(exc_val, exc_tb)

    assert ExplodingPlugin.raised
    assert len(catch_all_plugin.calls) == 1


def test_system_exit_in_observer_swallowed(system_exit_plugin, plugin_manager):
    """An observer raising SystemExit cannot kill conda's error path."""
    try:
        raise CondaError("test")
    except CondaError:
        _, exc_val, exc_tb = sys.exc_info()
        plugin_manager.invoke_exception_observers(exc_val, exc_tb)


def test_exception_event_is_frozen(catch_all_plugin, plugin_manager):
    """CondaExceptionEvent is a frozen dataclass -- attributes cannot be mutated."""
    try:
        raise CondaError("test")
    except CondaError:
        _, exc_val, exc_tb = sys.exc_info()
        plugin_manager.invoke_exception_observers(exc_val, exc_tb)

    info = catch_all_plugin.calls[0]
    with pytest.raises(AttributeError):
        info.return_code = 99


def test_invoked_via_exception_handler_class(catch_all_plugin, plugin_manager):
    """ExceptionHandler.handle_exception invokes exception observer plugins."""
    handler = ExceptionHandler()
    exc = CondaError("integration test")
    try:
        raise exc
    except CondaError:
        _, exc_val, exc_tb = sys.exc_info()
        handler.handle_exception(exc_val, exc_tb)

    assert len(catch_all_plugin.calls) == 1
    assert catch_all_plugin.calls[0].exc_value is exc


def test_invoked_for_unexpected_exception_path(
    base_exception_plugin, plugin_manager, monkeypatch
):
    """
    Non-CondaError exceptions route to ExceptionHandler.handle_unexpected_exception.
    The plugin hook fires at the top of handle_exception, before the isinstance
    chain, so plugins observe those too.
    """
    monkeypatch.setattr(
        ExceptionHandler, "print_unexpected_error_report", lambda self, report: None
    )
    handler = ExceptionHandler()
    exc = RuntimeError("not a conda error")
    try:
        raise exc
    except RuntimeError:
        _, exc_val, exc_tb = sys.exc_info()
        handler.handle_exception(exc_val, exc_tb)

    assert len(base_exception_plugin.calls) == 1
    info = base_exception_plugin.calls[0]
    assert info.exc_value is exc
    assert info.exc_type is RuntimeError


def test_no_observers_registered(plugin_manager):
    """Invocation is a no-op when no observers are registered."""
    try:
        raise CondaError("test")
    except CondaError:
        _, exc_val, exc_tb = sys.exc_info()
        plugin_manager.invoke_exception_observers(exc_val, exc_tb)


@pytest.mark.parametrize(
    "exc,return_code",
    [
        (ValueError("oops"), 1),
        (MemoryError(), 1),
        (KeyboardInterrupt(), 1),
        (SystemExit(2), 2),
        (SystemExit(42), 42),
    ],
)
def test_base_exception_plugin_dispatches_exception_types(
    base_exception_plugin,
    plugin_manager,
    exc,
    return_code,
):
    """An observer with watch_for={'BaseException'} fires for any exception type."""
    try:
        raise exc
    except BaseException:
        _, exc_val, exc_tb = sys.exc_info()
        plugin_manager.invoke_exception_observers(exc_val, exc_tb)

    assert len(base_exception_plugin.calls) == 1
    info = base_exception_plugin.calls[0]
    assert info.exc_value is exc
    assert info.exc_type is type(exc)
    assert info.return_code == return_code


def test_conda_error_not_matched_by_memory_error_observer(plugin_manager):
    """An observer with watch_for={'MemoryError'} does not fire for CondaError."""

    class MemoryErrorPlugin:
        def __init__(self):
            self.calls: list[CondaExceptionEvent] = []

        @plugins.hookimpl
        def conda_exception_observers(self):
            yield CondaExceptionObserver(
                name="memory-only",
                hook=self.calls.append,
                watch_for={"MemoryError"},
            )

    p = MemoryErrorPlugin()
    plugin_manager.register(p)

    try:
        raise CondaError("test")
    except CondaError:
        _, exc_val, exc_tb = sys.exc_info()
        plugin_manager.invoke_exception_observers(exc_val, exc_tb)

    assert len(p.calls) == 0


def test_combined_watch_for_scopes(plugin_manager):
    """An observer with watch_for={'CondaError', 'MemoryError'} fires for both types."""

    class CombinedPlugin:
        def __init__(self):
            self.calls: list[CondaExceptionEvent] = []

        @plugins.hookimpl
        def conda_exception_observers(self):
            yield CondaExceptionObserver(
                name="combined",
                hook=self.calls.append,
                watch_for={"CondaError", "MemoryError"},
            )

    p = CombinedPlugin()
    plugin_manager.register(p)

    try:
        raise CondaError("test")
    except CondaError:
        _, exc_val, exc_tb = sys.exc_info()
        plugin_manager.invoke_exception_observers(exc_val, exc_tb)

    try:
        raise MemoryError()
    except MemoryError:
        _, exc_val, exc_tb = sys.exc_info()
        plugin_manager.invoke_exception_observers(exc_val, exc_tb)

    assert len(p.calls) == 2
    assert p.calls[0].exc_type is CondaError
    assert p.calls[1].exc_type is MemoryError
