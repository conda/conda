# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda import CondaError, plugins
from conda._private.exception_guidance import GuidanceHint

if TYPE_CHECKING:
    from collections.abc import Iterator

    from conda.plugins.manager import CondaPluginManager


class ErrorHintsPlugin:
    def __init__(self):
        self.calls = []

    @plugins.hookimpl
    def conda_error_hints(
        self, error: CondaError
    ) -> Iterator[plugins.types.CondaErrorHint]:
        self.calls.append(error)
        yield plugins.types.CondaErrorHint("First hint.", "first_hint")
        yield plugins.types.CondaErrorHint("Second hint.", "second_hint")


class InvalidHintPlugin:
    def __init__(self, invalid_hint):
        self.invalid_hint = invalid_hint

    @plugins.hookimpl
    def conda_error_hints(self, error: CondaError):
        yield self.invalid_hint
        yield plugins.types.CondaErrorHint("Still valid.", "still_valid")


class ExplodingHintPlugin:
    @plugins.hookimpl
    def conda_error_hints(self, error: CondaError):
        raise RuntimeError("plugin bug")
        yield plugins.types.CondaErrorHint("unreachable", "unreachable")


class NamedErrorHintPlugin:
    def __init__(self, text: str, hint_code: str):
        self.text = text
        self.hint_code = hint_code

    @plugins.hookimpl
    def conda_error_hints(self, error: CondaError):
        yield plugins.types.CondaErrorHint(self.text, self.hint_code)


def test_get_error_hints(plugin_manager: CondaPluginManager):
    plugin = ErrorHintsPlugin()
    error = CondaError("boom")
    plugin_manager.register(plugin)

    assert plugin_manager.get_error_hints(error) == (
        GuidanceHint("First hint.", "first_hint"),
        GuidanceHint("Second hint.", "second_hint"),
    )
    assert plugin.calls == [error]


def test_get_error_hints_orders_plugins_by_plugin_name(
    plugin_manager: CondaPluginManager,
):
    plugin_manager.register(
        NamedErrorHintPlugin("Second plugin.", "second_plugin"),
        name="z-plugin",
    )
    plugin_manager.register(
        NamedErrorHintPlugin("First plugin.", "first_plugin"),
        name="a-plugin",
    )

    assert plugin_manager.get_error_hints(CondaError("boom")) == (
        GuidanceHint("First plugin.", "first_plugin"),
        GuidanceHint("Second plugin.", "second_plugin"),
    )


@pytest.mark.parametrize(
    "invalid_hint",
    [
        object(),
        {"text": "Dict hint.", "hint_code": "dict_hint"},
        GuidanceHint("Internal hint.", "internal_hint"),
    ],
)
def test_get_error_hints_ignores_invalid_hints(
    plugin_manager: CondaPluginManager,
    invalid_hint,
):
    plugin_manager.register(InvalidHintPlugin(invalid_hint))

    assert plugin_manager.get_error_hints(CondaError("boom")) == (
        GuidanceHint("Still valid.", "still_valid"),
    )


def test_get_error_hints_swallow_plugin_failures(
    plugin_manager: CondaPluginManager,
):
    plugin_manager.register(ExplodingHintPlugin())
    plugin_manager.register(ErrorHintsPlugin())

    assert plugin_manager.get_error_hints(CondaError("boom")) == (
        GuidanceHint("First hint.", "first_hint"),
        GuidanceHint("Second hint.", "second_hint"),
    )
