from __future__ import print_function, division, absolute_import

import sys
import logging

from conda.utils import memoized
from conda.progressbar import (Bar, ETA, FileTransferSpeed, Percentage,
                               ProgressBar)


fetch_progress = ProgressBar(
    widgets=['', ' ', Percentage(), ' ', Bar(), ' ', ETA(), ' ',
             FileTransferSpeed()])

progress = ProgressBar(widgets=['', ' ', Bar(), ' ', Percentage()])


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
        if record.name == 'progress.start':
            progress.maxval = record.msg
            progress.start()

        elif record.name == 'progress.update':
            name, n = record.msg
            progress.widgets[0] = '[%-20s]' % name
            progress.update(n)

        elif record.name == 'progress.stop':
            progress.widgets[0] = '[      COMPLETE      ]'
            progress.finish()


class PrintHandler(logging.Handler):
    def emit(self, record):
        if record.name == 'print':
            print(record.msg)

class DotHandler(logging.Handler):
    def emit(self, record):
        try:
            sys.stdout.write('.')
            sys.stdout.flush()
        except IOError:
            # sys.stdout.flush doesn't work in pythonw
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

@memoized  # to avoid setting up handlers more than once
def setup_verbose_handlers():
    fetch_prog_logger = logging.getLogger('fetch')
    fetch_prog_logger.setLevel(logging.INFO)
    fetch_prog_logger.addHandler(FetchProgressHandler())

    prog_logger = logging.getLogger('progress')
    prog_logger.setLevel(logging.INFO)
    prog_logger.addHandler(ProgressHandler())

    print_logger = logging.getLogger('print')
    print_logger.setLevel(logging.INFO)
    print_logger.addHandler(PrintHandler())

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
