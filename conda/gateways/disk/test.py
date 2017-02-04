# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from glob import glob
from logging import getLogger
from os import W_OK, access
from os.path import basename, dirname, isdir, isfile, islink, join, lexists

from .create import create_link
from .delete import rm_rf
from .update import touch
from ... import CondaError
from ..._vendor.auxlib.decorators import memoize
from ...models.enums import LinkType

log = getLogger(__name__)


def file_path_is_writable(path):
    if isdir(dirname(path)):
        try:
            touch(path)
        except (IOError, OSError) as e:
            log.debug(e)
            return False
        else:
            return True
    else:
        # TODO: probably won't work well on Windows
        return access(path, W_OK)


def prefix_is_writable(prefix):
    if isdir(prefix):
        history_file = join(prefix, 'conda-meta', 'history')
        if isfile(history_file):
            return file_path_is_writable(history_file)
        else:
            # history file doesn't exist, we created it, but we still can't be sure
            #  about the prefix
            # this probably only happens for the root environment with old installers
            # look at ownership of conda-*.json
            conda_json_files = glob(join(prefix, 'conda-meta', 'conda-*.json'))
            if conda_json_files:
                return file_path_is_writable(conda_json_files[0])
            else:
                # let's just look at any/first .json file in the directory
                all_json_files = glob(join(prefix, 'conda-meta', '*.json'))
                log.debug("probably not a conda prefix '%s'", prefix)
                if all_json_files:
                    return file_path_is_writable(all_json_files[0])
                else:
                    raise CondaError("Unable to determine if prefix '%s' is writable." % prefix)
    else:
        # TODO: probably won't work well on Windows
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
