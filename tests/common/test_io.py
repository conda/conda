# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from conda.common.io import attach_stderr_handler, captured
from logging import DEBUG, NOTSET, WARN, getLogger


def test_attach_stderr_handler():
    name = 'abbacadabba'
    logr = getLogger(name)
    assert len(logr.handlers) == 0
    assert logr.level is NOTSET

    debug_message = "debug message 1329-485"

    with captured() as c:
        attach_stderr_handler(WARN, name)
        logr.warn('test message')
        logr.debug(debug_message)

    assert len(logr.handlers) == 1
    assert logr.handlers[0].name == 'stderr'
    assert logr.handlers[0].level is NOTSET
    assert logr.level is WARN
    assert c.stdout == ''
    assert 'test message' in c.stderr
    assert debug_message not in c.stderr

    # round two, with debug
    with captured() as c:
        attach_stderr_handler(DEBUG, name)
        logr.warn('test message')
        logr.debug(debug_message)
        logr.info('info message')

    assert len(logr.handlers) == 1
    assert logr.handlers[0].name == 'stderr'
    assert logr.handlers[0].level is NOTSET
    assert logr.level is DEBUG
    assert c.stdout == ''
    assert 'test message' in c.stderr
    assert debug_message in c.stderr


