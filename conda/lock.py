# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

"""
Tools for working with locks

A lock is just an empty directory. We use directories because this lets us use
the race condition-proof os.makedirs.

For now, there is one global lock for all of conda, because some things happen
globally (such as downloading packages).

We don't raise an error if the lock is named with the current PID
"""
from __future__ import absolute_import, division, print_function

import logging
import os
import time
from glob import glob
from os.path import abspath, isdir, join

from conda.install import rm_rf
from .compat import range
from .exceptions import LockError

LOCKFN = '.conda_lock'

# Keep the string "LOCKERROR" in this string so that external
# programs can look for it.
LOCKSTR = """\
LOCKERROR: It looks like conda is already doing something.
The lock %s was found. Wait for it to finish before continuing.
If you are sure that conda is not running, remove it and try again.
You can also use: $ conda clean --lock
"""

stdoutlog = logging.getLogger('stdoutlog')
log = logging.getLogger(__name__)

def touch(fname, times=None):
    # http://stackoverflow.com/a/1160227/2127762
    with open(fname, 'a'):
        os.utime(fname, times)


class Locked(object):
    """
    Context manager to handle locks.
    """
    def __init__(self, path, retries=10):
        self.path = path
        self.end = "-" + str(os.getpid())
        self.lock_path = join(self.path, LOCKFN + self.end)
        self.retries = retries

    def __enter__(self):

        sleeptime = 1

        for _ in range(self.retries):
            if isdir(self.lock_path):
                stdoutlog.info(LOCKSTR % self.lock_path)
                stdoutlog.info("Sleeping for %s seconds\n" % sleeptime)

                time.sleep(sleeptime)
                sleeptime *= 2
            else:
                os.makedirs(self.lock_path)
                return self

        stdoutlog.error("Exceeded max retries, giving up")
        raise LockError(LOCKSTR % self.lock_path)

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            os.rmdir(self.lock_path)
            os.rmdir(self.path)
        except OSError:
            pass


class FileLock(object):
    """
    Context manager to handle locks.
    """
    def __init__(self, filepath, retries=10):
        self.filepath = abspath(filepath)
        self.retries = retries

    def __enter__(self):
        sleeptime = 1
        self.lockpath = "{0}.pid{1}.{2}".format(self.filepath, os.getpid(), LOCKFN)
        lockglobstr = "{0}.pid*.{2}".format(self.filepath, LOCKFN)
        lastglobmatch = None
        for _ in range(self.retries):
            globresult = glob(lockglobstr)
            if globresult:
                stdoutlog.info(LOCKSTR % globresult[0])
                stdoutlog.info("Sleeping for %s seconds\n" % sleeptime)

                time.sleep(sleeptime/10)
                sleeptime *= 2
                lastglobmatch = globresult
            else:
                touch(lockpath)
                return self

        stdoutlog.error("Exceeded max retries, giving up")
        raise LockError(LOCKSTR % lastglobmatch[0])

    def __exit__(self, exc_type, exc_value, traceback):
        rm_rf(self.lockpath)
