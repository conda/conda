# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import pytest

from conda.common.terminal import (
    force_color,
    is_interactive_tty,
    is_stderr_tty,
    is_stdin_tty,
    is_tty,
    no_color,
    should_use_color,
    term_dumb,
)


class FakeStream:
    def __init__(self, isatty_value: bool):
        self._isatty_value = isatty_value

    def isatty(self) -> bool:
        return self._isatty_value


@pytest.mark.parametrize(
    "term,expected",
    [("dumb", True), ("unknown", True), ("xterm-256color", False)],
)
def test_term_dumb_with_term(monkeypatch, term, expected):
    monkeypatch.setenv("TERM", term)
    assert term_dumb() is expected


def test_term_dumb_without_term(monkeypatch):
    monkeypatch.delenv("TERM", raising=False)
    assert term_dumb() is False


@pytest.mark.parametrize("value", ["", "1"])
def test_no_color_when_env_var_set(monkeypatch, value):
    monkeypatch.setenv("NO_COLOR", value)
    assert no_color() is True


def test_no_color_false_without_env_var(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "dumb")
    assert no_color() is False


def test_no_color_false_with_non_dumb_term(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    assert no_color() is False


@pytest.mark.parametrize("value", ["1", "true"])
def test_force_color_when_env_var_set(monkeypatch, value):
    monkeypatch.setenv("FORCE_COLOR", value)
    assert force_color() is True


@pytest.mark.parametrize("value", [None, ""])
def test_force_color_false(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("FORCE_COLOR", raising=False)
    else:
        monkeypatch.setenv("FORCE_COLOR", value)
    assert force_color() is False


@pytest.mark.parametrize(
    "term,no_color_value,force_color_value,is_tty_value,expected",
    [
        ("xterm-256color", "1", "1", True, False),
        ("xterm-256color", None, "1", False, True),
        ("dumb", None, "1", False, True),
        ("dumb", None, None, True, False),
        ("unknown", None, None, True, False),
        ("xterm-256color", None, "", False, False),
        ("xterm-256color", None, None, True, True),
        ("xterm-256color", None, None, False, False),
    ],
)
def test_should_use_color(
    monkeypatch, term, no_color_value, force_color_value, is_tty_value, expected
):
    monkeypatch.setenv("TERM", term)
    if no_color_value is None:
        monkeypatch.delenv("NO_COLOR", raising=False)
    else:
        monkeypatch.setenv("NO_COLOR", no_color_value)
    if force_color_value is None:
        monkeypatch.delenv("FORCE_COLOR", raising=False)
    else:
        monkeypatch.setenv("FORCE_COLOR", force_color_value)

    monkeypatch.setattr("conda.common.terminal.is_tty", lambda: is_tty_value)

    assert should_use_color() is expected


@pytest.mark.parametrize("stdout_value,expected", [(True, True), (False, False)])
def test_is_tty_checks_only_stdout(monkeypatch, stdout_value, expected):
    monkeypatch.setattr("sys.stdout", FakeStream(stdout_value))
    # stdin/stderr are intentionally left as the opposite value to prove
    # they're not consulted.
    monkeypatch.setattr("sys.stdin", FakeStream(not stdout_value))
    monkeypatch.setattr("sys.stderr", FakeStream(not stdout_value))
    assert is_tty() is expected


@pytest.mark.parametrize("stdin_value,expected", [(True, True), (False, False)])
def test_is_stdin_tty(monkeypatch, stdin_value, expected):
    monkeypatch.setattr("sys.stdin", FakeStream(stdin_value))
    # stdout/stderr are intentionally left as the opposite value to prove
    # they're not consulted.
    monkeypatch.setattr("sys.stdout", FakeStream(not stdin_value))
    monkeypatch.setattr("sys.stderr", FakeStream(not stdin_value))
    assert is_stdin_tty() is expected


@pytest.mark.parametrize("stderr_value,expected", [(True, True), (False, False)])
def test_is_stderr_tty(monkeypatch, stderr_value, expected):
    monkeypatch.setattr("sys.stderr", FakeStream(stderr_value))
    # stdout/stdin are intentionally left as the opposite value to prove
    # they're not consulted.
    monkeypatch.setattr("sys.stdout", FakeStream(not stderr_value))
    monkeypatch.setattr("sys.stdin", FakeStream(not stderr_value))
    assert is_stderr_tty() is expected


@pytest.mark.parametrize(
    "stdout_value,stdin_value,expected",
    [
        (True, True, True),
        (True, False, False),
        (False, True, False),
        (False, False, False),
    ],
)
def test_is_interactive_tty(monkeypatch, stdout_value, stdin_value, expected):
    monkeypatch.setattr("sys.stdout", FakeStream(stdout_value))
    monkeypatch.setattr("sys.stdin", FakeStream(stdin_value))
    assert is_interactive_tty() is expected


def test_is_stdin_false_when_isatty_missing(monkeypatch):
    monkeypatch.setattr("sys.stdin", object())
    assert is_stdin_tty() is False


def test_is_stderr_false_when_isatty_missing(monkeypatch):
    monkeypatch.setattr("sys.stderr", object())
    assert is_stderr_tty() is False
