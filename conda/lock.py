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

from .exceptions import LockError

LOCKFN = '.conda_lock'


stdoutlog = logging.getLogger('stdoutlog')


class Locked(object):
    """
    Context manager to handle locks.
    """
    def __init__(self, path, retries=10):
        self.path = path
        self.end = "-" + str(os.getpid())
        self.lock_path = os.path.join(self.path, LOCKFN + self.end)
        self.retries = retries

    def __enter__(self):
        # Keep the string "LOCKERROR" in this string so that external
        # programs can look for it.
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            os.rmdir(self.lock_path)
            os.rmdir(self.path)
        except OSError:
            pass
