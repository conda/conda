# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from conda.common.terminal import (
    force_color,
    no_color,
    should_use_color,
    term_dumb,
)


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


def test_no_color_when_term_dumb(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "dumb")
    assert no_color() is True


def test_no_color_false_without_env_vars(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("TERM", raising=False)
    assert no_color() is False


def test_no_color_false_with_non_dumb_term(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    assert no_color() is False


@pytest.mark.parametrize("value", ["1", ""])
def test_force_color_when_env_var_set(monkeypatch, value):
    monkeypatch.setenv("FORCE_COLOR", value)
    assert force_color() is True


def test_force_color_false_without_env_var(monkeypatch):
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    assert force_color() is False


def test_should_use_color_no_color_takes_precedence(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("FORCE_COLOR", "1")
    assert should_use_color() is False


@pytest.mark.parametrize(
    "is_tty_value,expected",
    [(False, True), (True, True)],
)
def test_should_use_color_force_color_or_tty(monkeypatch, is_tty_value, expected):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.setattr("conda.common.io.is_tty", lambda: is_tty_value)
    assert should_use_color() is expected


@pytest.mark.parametrize(
    "is_tty_value,expected",
    [(True, True), (False, False)],
)
def test_should_use_color_tty_only(monkeypatch, is_tty_value, expected):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.setattr("conda.common.io.is_tty", lambda: is_tty_value)
    assert should_use_color() is expected
