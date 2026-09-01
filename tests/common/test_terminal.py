# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import pytest

from conda.common.terminal import (
    force_color,
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
def test_is_tty_default_only_checks_stdout(monkeypatch, stdout_value, expected):
    monkeypatch.setattr("sys.stdout", FakeStream(stdout_value))
    # stdin is intentionally left as the opposite value to prove it's not consulted.
    monkeypatch.setattr("sys.stdin", FakeStream(not stdout_value))
    monkeypatch.setattr("sys.stderr", FakeStream(not stdout_value))
    assert is_tty() is expected


@pytest.mark.parametrize(
    "stdout_value,stdin_value,expected",
    [
        (True, True, True),
        (True, False, False),
        (False, True, False),
        (False, False, False),
    ],
)
def test_is_tty_include_stdin(monkeypatch, stdout_value, stdin_value, expected):
    monkeypatch.setattr("sys.stdout", FakeStream(stdout_value))
    monkeypatch.setattr("sys.stdin", FakeStream(stdin_value))
    assert is_tty(include_stdin=True) is expected


@pytest.mark.parametrize(
    "stdout_value,stderr_value,expected",
    [
        (True, True, True),
        (True, False, False),
        (False, True, False),
        (False, False, False),
    ],
)
def test_is_tty_include_stderr(monkeypatch, stdout_value, stderr_value, expected):
    monkeypatch.setattr("sys.stdout", FakeStream(stdout_value))
    monkeypatch.setattr("sys.stderr", FakeStream(stderr_value))
    assert is_tty(include_stderr=True) is expected


def test_is_tty_include_stdin_and_stderr_all_true(monkeypatch):
    monkeypatch.setattr("sys.stdout", FakeStream(True))
    monkeypatch.setattr("sys.stdin", FakeStream(True))
    monkeypatch.setattr("sys.stderr", FakeStream(True))
    assert is_tty(include_stdin=True, include_stderr=True) is True


@pytest.mark.parametrize(
    "stdout_value,stdin_value,stderr_value",
    [
        (False, True, True),
        (True, False, True),
        (True, True, False),
    ],
)
def test_is_tty_include_stdin_and_stderr_any_false(
    monkeypatch, stdout_value, stdin_value, stderr_value
):
    monkeypatch.setattr("sys.stdout", FakeStream(stdout_value))
    monkeypatch.setattr("sys.stdin", FakeStream(stdin_value))
    monkeypatch.setattr("sys.stderr", FakeStream(stderr_value))
    assert is_tty(include_stdin=True, include_stderr=True) is False


def test_is_tty_rejects_positional_args():
    with pytest.raises(TypeError):
        is_tty(True)
    with pytest.raises(TypeError):
        is_tty(True, True)


def test_is_tty_returns_false_without_isatty_attr(monkeypatch):
    monkeypatch.setattr("sys.stdout", FakeStream(True))
    monkeypatch.setattr("sys.stdin", object())
    assert is_tty(include_stdin=True) is False
