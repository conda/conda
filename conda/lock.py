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

"""

from __future__ import print_function, division, absolute_import

from os.path import join
from os import rmdir, makedirs

import errno

from conda import config


def create_lock(path, name):
    """
    Creates a lock at `path`. Returns True if the file was created and
    False if the file already exists.
    """
    # Note, we do this instead of os.path.exists to avoid race conditions
    try:
        makedirs(join(path, name))
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise RuntimeError("LOCKERROR: Could not create the lock %s: %s" %
                (join(path, name), e.strerror))
        return False
    return True

def remove_lock(path, name):
    # Intentionally raise an exception if the directory is not there, or if it
    # is nonempty.
    rmdir(join(path, name))

class Locked(object):
    """
    Context manager to handle locks.
    """
    def __init__(self, path=config.root_dir, name=".conda_lock"):
        self.path = path
        self.name = name

    def __enter__(self):
        lock = create_lock(self.path, self.name)
        if not lock:
            # Keep the string "LOCKERROR" in this string so that external
            # programs can look for it.
            raise RuntimeError(("LOCKERROR: It looks like conda is already doing "
                "something.  The lock %s was found. Wait for it to finish "
                "before continuing. If you are sure that conda is not running, "
                "remove it and try again."
                ) % (join(self.path, self.name, '')))

    def __exit__(self, exc_type, exc_value, traceback):
        remove_lock(self.path, self.name)
        try:
            # Remove the locked path if it is empty, since this means that it
            # did not exist when we created the lock.
            rmdir(self.path)
        except OSError:
            pass
