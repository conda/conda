from __future__ import print_function, division, absolute_import

import os
import sys
import json
import logging
import contextlib

from conda.utils import memoized
from conda.progressbar import (Bar, ETA, FileTransferSpeed, Percentage,
                               ProgressBar)


try:
    tty = open(os.ctermid(), 'w')
except (IOError, AttributeError):
    # apparently `os.ctermid` not available on Windows, and throws AttributeError
    tty = sys.stdout

fetch_progress = ProgressBar(widgets=['', ' ', Percentage(), ' ', Bar(),
                                      ' ', ETA(), ' ', FileTransferSpeed()],
                             fd=tty)

progress = ProgressBar(widgets=['[%-20s]' % '', '', Bar(), ' ', Percentage()],
                       fd=tty)


class FetchProgressHandler(logging.Handler):

    def emit(self, record):
        if record.name == 'fetch.start':
            filename, maxval = record.msg
            fetch_progress.widgets[0] = filename
            fetch_progress.maxval = maxval
            fetch_progress.start()

        elif record.name == 'fetch.update':
            n = record.msg
            fetch_progress.update(n)

        elif record.name == 'fetch.stop':
            fetch_progress.finish()


class ProgressHandler(logging.Handler):

    def emit(self, record):
        try:
            if record.name == 'progress.start':
                progress.maxval = record.msg
                progress.start()

            elif record.name == 'progress.update':
                name, n = record.msg
                progress.widgets[0] = '[%-20s]' % name
                if n == 0:
                    # Make sure the widget gets updated
                    progress.start()
                progress.update(n)

            elif record.name == 'progress.stop':
                progress.widgets[0] = '[      COMPLETE      ]'
                progress.finish()
        except LookupError:
            pass

class JsonFetchProgressHandler(logging.Handler):
    def emit(self, record):
        if record.name == 'fetch.start':
            filename, maxval = record.msg
            print(json.dumps({
                'fetch': filename,
                'maxval': maxval,
                'progress': 0,
                'finished': False
            }))
            print('\0', end='')
            sys.stdout.flush()
            self.filename = filename
            self.maxval = maxval

        elif record.name == 'fetch.update':
            n = record.msg
            print(json.dumps({
                'fetch': self.filename,
                'maxval': self.maxval,
                'progress': n,
                'finished': False
            }))
            print('\0', end='')
            sys.stdout.flush()

        elif record.name == 'fetch.stop':
            print(json.dumps({
                'fetch': self.filename,
                'maxval': self.maxval,
                'progress': self.maxval,
                'finished': True
            }))
            print('\0', end='')
            sys.stdout.flush()
            self.filename = None
            self.maxval = -1


class JsonProgressHandler(logging.Handler):

    def emit(self, record):
        if record.name == 'progress.start':
            maxval = record.msg
            print(json.dumps({
                'maxval': maxval,
                'progress': 0,
                'finished': False
            }))
            print('\0', end='')
            sys.stdout.flush()
            self.maxval = maxval

        elif record.name == 'progress.update':
            name, n = record.msg
            print(json.dumps({
                'name': name,
                'maxval': self.maxval,
                'progress': n,
                'finished': False
            }))
            print('\0', end='')
            sys.stdout.flush()

        elif record.name == 'progress.stop':
            print(json.dumps({
                'maxval': self.maxval,
                'progress': self.maxval,
                'finished': True
            }))
            print('\0', end='')
            sys.stdout.flush()


class PrintHandler(logging.Handler):
    def emit(self, record):
        if record.name == 'print':
            print(record.msg)

class DotHandler(logging.Handler):
    def emit(self, record):
        try:
            tty.write('.')
            tty.flush()
        except IOError:
            pass

class SysStdoutWriteHandler(logging.Handler):
    def emit(self, record):
        try:
            sys.stdout.write(record.msg)
            sys.stdout.flush()
        except IOError:
            pass


class SysStderrWriteHandler(logging.Handler):
    def emit(self, record):
        try:
            sys.stderr.write(record.msg)
            sys.stderr.flush()
        except IOError:
            pass

_fetch_prog_handler = FetchProgressHandler()
_prog_handler = ProgressHandler()

@memoized  # to avoid setting up handlers more than once
def setup_verbose_handlers():
    fetch_prog_logger = logging.getLogger('fetch')
    fetch_prog_logger.setLevel(logging.INFO)
    fetch_prog_logger.addHandler(_fetch_prog_handler)

    prog_logger = logging.getLogger('progress')
    prog_logger.setLevel(logging.INFO)
    prog_logger.addHandler(_prog_handler)

    print_logger = logging.getLogger('print')
    print_logger.setLevel(logging.INFO)
    print_logger.addHandler(PrintHandler())

@contextlib.contextmanager
def json_progress_bars():
    setup_verbose_handlers()
    fetch_prog_logger = logging.getLogger('fetch')
    prog_logger = logging.getLogger('progress')
    print_logger = logging.getLogger('print')

    # Disable this. Presumably this function is being used in a CLI context
    # with --json, so we don't want the logger enabled (but we just
    # activated it)
    print_logger.setLevel(logging.CRITICAL + 1)

    json_fetch_prog_handler = JsonFetchProgressHandler()
    json_prog_handler = JsonProgressHandler()

    fetch_prog_logger.removeHandler(_fetch_prog_handler)
    prog_logger.removeHandler(_prog_handler)
    fetch_prog_logger.addHandler(json_fetch_prog_handler)
    prog_logger.addHandler(json_prog_handler)

    yield

    fetch_prog_logger.removeHandler(json_fetch_prog_handler)
    prog_logger.removeHandler(json_prog_handler)
    fetch_prog_logger.addHandler(_fetch_prog_handler)
    prog_logger.addHandler(_prog_handler)

@memoized
def setup_handlers():
    dotlogger = logging.getLogger('dotupdate')
    dotlogger.setLevel(logging.DEBUG)
    dotlogger.addHandler(DotHandler())

    stdoutlogger = logging.getLogger('stdoutlog')
    stdoutlogger.setLevel(logging.DEBUG)
    stdoutlogger.addHandler(SysStdoutWriteHandler())

    stderrlogger = logging.getLogger('stderrlog')
    stderrlogger.setLevel(logging.DEBUG)
    stderrlogger.addHandler(SysStderrWriteHandler())
