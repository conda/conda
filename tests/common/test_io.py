# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import sys
import time
from concurrent.futures import ThreadPoolExecutor
from io import StringIO
from logging import DEBUG, NOTSET, WARN, getLogger

import pytest

from conda.common.io import (
    CaptureTarget,
    ThreadLimitedThreadPoolExecutor,
    attach_stderr_handler,
    captured,
    force_color,
    no_color,
    should_use_color,
    term_dumb,
)


def test_captured():
    stdout_text = "stdout text"
    stderr_text = "stderr text"

    def print_captured(*args, **kwargs):
        with captured(*args, **kwargs) as c:
            print(stdout_text, end="")
            print(stderr_text, end="", file=sys.stderr)
        return c

    c = print_captured()
    assert c.stdout == stdout_text
    assert c.stderr == stderr_text

    c = print_captured(CaptureTarget.STRING, CaptureTarget.STRING)
    assert c.stdout == stdout_text
    assert c.stderr == stderr_text

    c = print_captured(stderr=CaptureTarget.STDOUT)
    assert c.stdout == stdout_text + stderr_text
    assert c.stderr is None

    caller_stdout = StringIO()
    caller_stderr = StringIO()
    c = print_captured(caller_stdout, caller_stderr)
    assert c.stdout is caller_stdout
    assert c.stderr is caller_stderr
    assert caller_stdout.getvalue() == stdout_text
    assert caller_stderr.getvalue() == stderr_text

    with captured() as outer_c:
        inner_c = print_captured(None, None)
    assert inner_c.stdout is None
    assert inner_c.stderr is None
    assert outer_c.stdout == stdout_text
    assert outer_c.stderr == stderr_text


def test_attach_stderr_handler():
    name = "abbacadabba"
    logr = getLogger(name)
    assert len(logr.handlers) == 0
    assert logr.level is NOTSET

    debug_message = "debug message 1329-485"

    with captured() as c:
        attach_stderr_handler(WARN, name)
        logr.warning("test message")
        logr.debug(debug_message)

    assert len(logr.handlers) == 1
    assert logr.handlers[0].name == "stderr"
    assert logr.handlers[0].level is WARN
    assert logr.level is NOTSET
    assert logr.getEffectiveLevel() is WARN
    assert c.stdout == ""
    assert "test message" in c.stderr
    assert debug_message not in c.stderr

    # round two, with debug
    with captured() as c:
        attach_stderr_handler(DEBUG, name)
        logr.warning("test message")
        logr.debug(debug_message)
        logr.info("info message")

    assert len(logr.handlers) == 1
    assert logr.handlers[0].name == "stderr"
    assert logr.handlers[0].level is DEBUG
    assert logr.level is DEBUG
    assert c.stdout == ""
    assert "test message" in c.stderr
    assert debug_message in c.stderr


@pytest.mark.parametrize(
    "thread_class,should_fail",
    [
        (ThreadLimitedThreadPoolExecutor, False),
        (ThreadPoolExecutor, True),
    ],
)
def test_thread_limited_executor_handles_thread_limit(
    thread_class, should_fail, mocker
):
    """
    Ensure our custom ThreadLimitedThreadPoolExecutor class does what it is
    intended to do, which is not raise a RuntimeError if the max workers limit
    is reached.

    This only affects users of particular systems like HPC clusters.

    Some historical background can be found here:
        - https://github.com/conda/conda/pull/6653
        - https://github.com/conda/conda/issues/7040
    """
    jobs = 10

    if should_fail:
        mocker.patch(
            "concurrent.futures.ThreadPoolExecutor._adjust_thread_count",
            side_effect=[None, None, None, RuntimeError],
        )

        with thread_class() as executor:
            if should_fail:
                with pytest.raises(RuntimeError):
                    _ = [executor.submit(time.sleep, 0.1) for _ in range(jobs)]
            else:
                _ = [executor.submit(time.sleep, 0.1) for _ in range(jobs)]


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
