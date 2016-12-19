# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
from os import W_OK, access, getpid
from os.path import basename, isdir, isfile, islink, join, lexists

from .create import create_link
from .delete import backoff_unlink, rm_rf
from ..._vendor.auxlib.decorators import memoize
from ...common.compat import on_win
from ...models.enums import LinkType

log = getLogger(__name__)


@memoize
def try_write(dir_path, heavy=False):
    """Test write access to a directory.

    Args:
        dir_path (str): directory to test write access
        heavy (bool): Actually create and delete a file, or do a faster os.access test.
           https://docs.python.org/dev/library/os.html?highlight=xattr#os.access

    Returns:
        bool

    """
    log.trace('checking user write access for %s', dir_path)
    if not isdir(dir_path):
        return False
    if on_win or heavy:
        # try to create a file to see if `dir_path` is writable, see #2151
        temp_filename = join(dir_path, '.conda-try-write-%d' % getpid())
        try:
            with open(temp_filename, mode='wb') as fo:
                fo.write(b'This is a test file.\n')
            backoff_unlink(temp_filename)
            return True
        except (IOError, OSError):
            return False
        finally:
            backoff_unlink(temp_filename)
    else:
        return access(dir_path, W_OK)


@memoize
def hardlink_supported(source_file, dest_dir):
    # Some file systems (e.g. BeeGFS) do not support hard-links
    # between files in different directories. Depending on the
    # file system configuration, a symbolic link may be created
    # instead. If a symbolic link is created instead of a hard link,
    # return False.
    log.trace("checking hard link capability for %s => %s", source_file, dest_dir)
    test_file = join(dest_dir, '.tmp.' + basename(source_file))
    assert isfile(source_file), source_file
    assert isdir(dest_dir), dest_dir
    assert not lexists(test_file), test_file
    try:
        create_link(source_file, test_file, LinkType.hardlink, force=True)
        return not islink(test_file)
    except (IOError, OSError):
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
