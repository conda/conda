# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import defaultdict
from contextlib import contextmanager
from functools import wraps
import json
import logging
from logging import CRITICAL, Formatter, NOTSET, StreamHandler, WARN, getLogger
import os
from os import chdir, getcwd
from os.path import dirname, isdir, isfile, join
import sys
from time import time

from .compat import StringIO
from .path import expand
from .._vendor.auxlib.decorators import memoizemethod
from .._vendor.auxlib.logz import NullHandler
from .._vendor.auxlib.type_coercion import boolify

log = getLogger(__name__)

_FORMATTER = Formatter("%(levelname)s %(name)s:%(funcName)s(%(lineno)d): %(message)s")


@contextmanager
def env_var(name, value, callback=None):
    # NOTE: will likely want to call reset_context() when using this function, so pass
    #       it as callback
    name, value = str(name), str(value)
    saved_env_var = os.environ.get(name)
    try:
        os.environ[name] = value
        if callback:
            callback()
        yield
    finally:
        if saved_env_var:
            os.environ[name] = saved_env_var
        else:
            del os.environ[name]
        if callback:
            callback()


@contextmanager
def cwd(directory):
    saved_cwd = getcwd()
    try:
        chdir(directory)
        yield
    finally:
        chdir(saved_cwd)


@contextmanager
def captured():
    # NOTE: This function is not thread-safe.  Using within multi-threading may cause spurious
    # behavior of not returning sys.stdout and sys.stderr back to their 'proper' state
    class CapturedText(object):
        pass
    saved_stdout, saved_stderr = sys.stdout, sys.stderr
    sys.stdout = outfile = StringIO()
    sys.stderr = errfile = StringIO()
    c = CapturedText()
    log.info("overtaking stderr and stdout")
    try:
        yield c
    finally:
        c.stdout, c.stderr = outfile.getvalue(), errfile.getvalue()
        sys.stdout, sys.stderr = saved_stdout, saved_stderr
        log.info("stderr and stdout yielding back")


@contextmanager
def replace_log_streams():
    # replace the logger stream handlers with stdout and stderr handlers
    stdout_logger, stderr_logger = getLogger('stdout'), getLogger('stderr')
    saved_stdout_strm = stdout_logger.handlers[0].stream
    saved_stderr_strm = stderr_logger.handlers[0].stream
    stdout_logger.handlers[0].stream = sys.stdout
    stderr_logger.handlers[0].stream = sys.stderr
    try:
        yield
    finally:
        # replace the original streams
        stdout_logger.handlers[0].stream = saved_stdout_strm
        stderr_logger.handlers[0].stream = saved_stderr_strm


@contextmanager
def argv(args_list):
    saved_args = sys.argv
    sys.argv = args_list
    try:
        yield
    finally:
        sys.argv = saved_args


@contextmanager
def _logger_lock():
    logging._acquireLock()
    try:
        yield
    finally:
        logging._releaseLock()


@contextmanager
def disable_logger(logger_name):
    logr = getLogger(logger_name)
    _hndlrs, _lvl, _dsbld, _prpgt = logr.handlers, logr.level, logr.disabled, logr.propagate
    with _logger_lock():
        logr.addHandler(NullHandler())
        logr.setLevel(CRITICAL + 1)
        logr.disabled, logr.propagate = True, False
    try:
        yield
    finally:
        with _logger_lock():
            logr.handlers, logr.level, logr.disabled = _hndlrs, _lvl, _dsbld
            logr.propagate = _prpgt


@contextmanager
def stderr_log_level(level, logger_name=None):
    logr = getLogger(logger_name)
    _hndlrs, _lvl, _dsbld, _prpgt = logr.handlers, logr.level, logr.disabled, logr.propagate
    handler = StreamHandler(sys.stderr)
    handler.name = 'stderr'
    handler.setLevel(level)
    handler.setFormatter(_FORMATTER)
    with _logger_lock():
        logr.setLevel(level)
        logr.handlers, logr.disabled, logr.propagate = [], False, False
        logr.addHandler(handler)
        logr.setLevel(level)
    try:
        yield
    finally:
        with _logger_lock():
            logr.handlers, logr.level, logr.disabled = _hndlrs, _lvl, _dsbld
            logr.propagate = _prpgt


def attach_stderr_handler(level=WARN, logger_name=None, propagate=False, formatter=None):
    # get old stderr logger
    logr = getLogger(logger_name)
    old_stderr_handler = next((handler for handler in logr.handlers if handler.name == 'stderr'),
                              None)

    # create new stderr logger
    new_stderr_handler = StreamHandler(sys.stderr)
    new_stderr_handler.name = 'stderr'
    new_stderr_handler.setLevel(NOTSET)
    new_stderr_handler.setFormatter(formatter or _FORMATTER)

    # do the switch
    with _logger_lock():
        if old_stderr_handler:
            logr.removeHandler(old_stderr_handler)
        logr.addHandler(new_stderr_handler)
        logr.setLevel(level)
        logr.propagate = propagate


class ContextDecorator(object):
    def __call__(self, f):
        @wraps(f)
        def decorated(*args, **kwds):
            with self:
                return f(*args, **kwds)
        return decorated


class time_recorder(ContextDecorator):  # pragma: no cover
    start_time = None
    record_file = expand(join('~', '.conda', 'instrumentation-record.csv'))

    def __init__(self, entry_name):
        self.entry_name = entry_name

    def __enter__(self):
        enabled = os.environ.get('CONDA_INSTRUMENTATION_ENABLED')
        if enabled and boolify(enabled):
            self.start_time = time()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            end_time = time()
            run_time = end_time - self.start_time
            self._ensure_dir()
            with open(self.record_file, 'a') as fh:
                fh.write("%s,%s\n" % (self.entry_name, run_time))

    @memoizemethod
    def _ensure_dir(self):
        if not isdir(dirname(self.record_file)):
            os.makedirs(dirname(self.record_file))


def print_instrumentation_data():  # pragma: no cover
    record_file = expand(join('~', '.conda', 'instrumentation-record.csv'))

    grouped_data = defaultdict(list)
    final_data = {}

    if not isfile(record_file):
        return

    with open(record_file) as fh:
        for line in fh:
            entry_name, total_time = line.strip().split(',')
            grouped_data[entry_name].append(float(total_time))

    for entry_name in sorted(grouped_data):
        all_times = grouped_data[entry_name]
        counts = len(all_times)
        total_time = sum(all_times)
        average_time = total_time / counts
        final_data[entry_name] = {
            'counts': counts,
            'total_time': total_time,
            'average_time': average_time,
        }

    print(json.dumps(final_data, sort_keys=True, indent=2, separators=(',', ': ')))


if __name__ == "__main__":
    print_instrumentation_data()
