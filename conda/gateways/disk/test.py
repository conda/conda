# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
from os import W_OK, access
from os.path import basename, dirname, isdir, isfile, join, lexists

from .create import create_link
from .delete import rm_rf
from .link import islink
from .read import find_first_existing
from ... import CondaError
from ..._vendor.auxlib.decorators import memoize
from ..._vendor.auxlib.path import expand
from ...common.path import get_python_short_path
from ...models.enums import LinkType

log = getLogger(__name__)


def file_path_is_writable(path):
    path = expand(path)
    log.trace("checking path is writable %s", path)
    if isdir(dirname(path)):
        path_existed = lexists(path)
        try:
            fh = open(path, 'a+')
        except (IOError, OSError) as e:
            log.debug(e)
            return False
        else:
            fh.close()
            if not path_existed:
                rm_rf(path)
            return True
    else:
        # TODO: probably won't work well on Windows
        return access(path, W_OK)


def prefix_is_writable(prefix):
    """
    Strategy:
      We use specific key files, not directory permissions, to determine the ownership of a prefix.
      (1) With conda constructor 1.5.4 and Anaconda and miniconda installers after 4.3, any prefix
          created by conda or a conda installer should have a `conda-meta/history` file.
      (2) If there is no `conda-meta/history` file, we look for a `conda-meta/conda-*.json` file,
          which exists for installers 4.3 and earlier.
      (3) If that doesn't exist, the prefix is probably one created by conda constructor that
          doesn't have conda installed in it.  In this case, we look for the first
          `conda-meta/*.json` file.
      (4) If that doesn't exist, then the current execution context is probably using a python
          interpreter that really isn't associated with a conda prefix.  We'll look at ownership
          of the python interpreter itself.

    """
    if isdir(prefix):
        test_path = find_first_existing(
            join(prefix, 'conda-meta', 'history'),  # (1)
            join(prefix, 'conda-meta', 'conda-*.json'),  # (2)
            join(prefix, 'conda-meta', '*.json'),  # (3)
            join(prefix, get_python_short_path('*')),  # (4)
        )
        log.debug("testing write access for prefix '%s' using path '%s'", prefix, test_path)
        if test_path is None:
            raise CondaError("Unable to determine if prefix '%s' is writable." % prefix)
        return file_path_is_writable(test_path)
    else:
        # TODO: probably won't work well on Windows
        log.debug("testing write access for prefix '%s' using prefix directory", prefix)
        return access(prefix, W_OK)


@memoize
def hardlink_supported(source_file, dest_dir):
    # Some file systems (e.g. BeeGFS) do not support hard-links
    # between files in different directories. Depending on the
    # file system configuration, a symbolic link may be created
    # instead. If a symbolic link is created instead of a hard link,
    # return False.
    test_file = join(dest_dir, '.tmp.' + basename(source_file))
    assert isfile(source_file), source_file
    assert isdir(dest_dir), dest_dir
    assert not lexists(test_file), test_file
    try:
        create_link(source_file, test_file, LinkType.hardlink, force=True)
        is_supported = not islink(test_file)
        if is_supported:
            log.trace("hard link supported for %s => %s", source_file, dest_dir)
        else:
            log.trace("hard link IS NOT supported for %s => %s", source_file, dest_dir)
        return is_supported
    except (IOError, OSError):
        log.trace("hard link IS NOT supported for %s => %s", source_file, dest_dir)
        return False
    finally:
        rm_rf(test_file)


@memoize
def softlink_supported(source_file, dest_dir):
    # On Windows, softlink creation is restricted to Administrative users by default. It can
    # optionally be enabled for non-admin users through explicit registry modification.
    log.trace("checking soft link capability for %s => %s", source_file, dest_dir)
    test_path = join(dest_dir, '.tmp.' + basename(source_file))
    assert isfile(source_file), source_file
    assert isdir(dest_dir), dest_dir
    assert not lexists(test_path), test_path
    try:
        create_link(source_file, test_path, LinkType.softlink, force=True)
        return islink(test_path)
    except (IOError, OSError):
        return False
    finally:
        rm_rf(test_path)
