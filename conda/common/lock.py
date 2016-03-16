# -*- coding: utf-8 -*-
"""
Tools for working with locks

A lock is just an empty directory. We use directories because this lets us use
the race condition-proof os.makedirs.

For now, there is one global lock for all of conda, because some things happen
globally (such as downloading packages).

We don't raise an error if the lock is named with the current PID
"""
from __future__ import absolute_import, division, print_function

import glob
import os
from logging import getLogger
from os.path import join
from time import sleep

log = getLogger(__name__)
stdoutlog = getLogger('stdoutlog')

LOCKFN = '.conda_lock'


class Locked(object):
    """
    Context manager to handle locks.
    """
    def __init__(self, path):
        self.path = path
        self.end = "-" + str(os.getpid())
        self.lock_path = join(self.path, LOCKFN + self.end)
        self.pattern = join(self.path, LOCKFN + '-*')
        self.remove = True

    def __enter__(self):
        retries = 10
        # Keep the string "LOCKERROR" in this string so that external
        # programs can look for it.
        lockstr = ("""\
    LOCKERROR: It looks like conda is already doing something.
    The lock %s was found. Wait for it to finish before continuing.
    If you are sure that conda is not running, remove it and try again.
    You can also use: $ conda clean --lock\n""")
        sleeptime = 1
        files = None
        while retries:
            files = glob.glob(self.pattern)
            if files and not files[0].endswith(self.end):
                stdoutlog.info(lockstr % str(files))
                stdoutlog.info("Sleeping for %s seconds\n" % sleeptime)
                sleep(sleeptime)
                sleeptime *= 2
                retries -= 1
            else:
                break
        else:
            stdoutlog.error("Exceeded max retries, giving up")
            raise RuntimeError(lockstr % str(files))

        if not files:
            try:
                os.makedirs(self.lock_path)
            except OSError:
                pass
        else: # PID lock already here --- someone else will remove it.
            self.remove = False

    def __exit__(self, exc_type, exc_value, traceback):
        if self.remove:
            for path in self.lock_path, self.path:
                try:
                    os.rmdir(path)
                except OSError:
                    pass
