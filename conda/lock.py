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
from os.path import abspath, isdir, dirname, basename, join
from .compat import range
from .exceptions import LockError

LOCK_EXTENSION = 'conda_lock'

# Keep the string "LOCKERROR" in this string so that external
# programs can look for it.
LOCKSTR = """
LOCKERROR: It looks like conda is already doing something.
The lock {0} was found. Wait for it to finish before continuing.
If you are sure that conda is not running, remove it and try again.
You can also use: $ conda clean --lock
"""

stdoutlog = logging.getLogger('stdoutlog')
log = logging.getLogger(__name__)

def touch(file_name, times=None):
    """ Touch function like touch in Unix shell
    :param file_name: the name of file
    :param times: the access and modified time
    Examples:
        touch("hello_world.py")
    """
    with open(file_name, 'a'):
        os.utime(file_name, times)


class FileLock(object):
    """
    Context manager to handle locks.
    """
    def __init__(self, file_path, retries=10):
        """
        :param file_path: The file or directory to be locked
        :param retries: max number of retries
        :return:
        """
        self.file_path = abspath(file_path)
        self.retries = retries
        self.lock_path = "%s.pid{0}.%s" % (self.file_path, LOCK_EXTENSION)
        self.lock_glob_str = "%s.pid*.%s" % (self.file_path, LOCK_EXTENSION)
        assert isdir(dirname(self.file_path)), "{0} doesn't exist".format(self.file_path)
        assert "::" not in self.file_path, self.file_path

    def __enter__(self):
        sleep_time = 1
        self.lock_path = self.lock_path.format(os.getpid())
        last_glob_match = None

        for _ in range(self.retries + 1):

            # search, whether there is process already locked on this file
            glob_result = glob(self.lock_glob_str)
            if glob_result:
                log.debug(LOCKSTR.format(glob_result))
                log.debug("Sleeping for %s seconds\n" % sleep_time)

                time.sleep(sleep_time / 10)
                sleep_time *= 2
                last_glob_match = glob_result
            else:
                touch(self.lock_path)
                return self

        stdoutlog.error("Exceeded max retries, giving up")
        raise LockError(LOCKSTR.format(last_glob_match))

    def __exit__(self, exc_type, exc_value, traceback):
        from .install import rm_rf
        rm_rf(self.lock_path)


class DirectoryLock(FileLock):

    def __init__(self, directory_path, retries=10):
        self.directory_path = abspath(directory_path)
        directory_name = basename(self.directory_path)
        self.retries = retries
        lock_path_pre = join(self.directory_path, directory_name)
        self.lock_path = "%s.pid{0}.%s" % (lock_path_pre, LOCK_EXTENSION)
        self.lock_glob_str = "%s.pid*.%s" % (lock_path_pre, LOCK_EXTENSION)
        assert isdir(dirname(self.directory_path)), "{0} doesn't exist".format(self.directory_path)
        assert os.access(self.directory_path, os.W_OK), "{0} not writable".format(self.directory_path)


Locked = DirectoryLock

