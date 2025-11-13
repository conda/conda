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
