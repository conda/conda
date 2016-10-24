# (c) 2012-2014 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
""" This module contains:
  * all low-level code for extracting, linking and unlinking packages
  * a very simple CLI

These API functions have argument names referring to:

    dist:        canonical package name (e.g. 'numpy-1.6.2-py26_0')

    pkgs_dir:    the "packages directory" (e.g. '/opt/anaconda/pkgs' or
                 '/home/joe/envs/.pkgs')

    prefix:      the prefix of a particular environment, which may also
                 be the "default" environment (i.e. sys.prefix),
                 but is otherwise something like '/opt/anaconda/envs/foo',
                 or even any prefix, e.g. '/home/joe/myenv'
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import errno
import functools
import logging
import os
import re
import shlex
import shutil
import stat
import struct
import subprocess
import sys
import traceback
from collections import namedtuple
from enum import Enum
from itertools import chain
from os.path import (abspath, basename, dirname, isdir, isfile, islink, join, normcase,
                     normpath)

from . import CondaError
from .base.constants import UTF8, PREFIX_PLACEHOLDER
from .base.context import context
from .common.disk import exp_backoff_fn, rm_rf, yield_lines
from .core.linked_data import create_meta, delete_linked_data, load_meta
from .core.package_cache import is_extracted
from .exceptions import CondaOSError, LinkError, PaddingError
from .lock import DirectoryLock, FileLock
from .models.dist import Dist
from .utils import on_win
from .noarch import get_noarch_cls

# conda-build compatibility
from .common.disk import delete_trash, move_path_to_trash  # NOQA
delete_trash, move_path_to_trash = delete_trash, move_path_to_trash
from .core.linked_data import is_linked, linked, linked_data  # NOQA
is_linked, linked, linked_data = is_linked, linked, linked_data
from .core.package_cache import package_cache, rm_fetched  # NOQA
rm_fetched, package_cache = rm_fetched, package_cache


log = logging.getLogger(__name__)
stdoutlog = logging.getLogger('stdoutlog')







class FileType(Enum):
    regular = 'regular'
    softlink = 'softlink'
    hardlink = 'hardlink'
    directory = 'directory'





def _remove_readonly(func, path, excinfo):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def warn_failed_remove(function, path, exc_info):
    if exc_info[1].errno == errno.EACCES:
        log.warn("Cannot remove, permission denied: {0}".format(path))
    elif exc_info[1].errno == errno.ENOTEMPTY:
        log.warn("Cannot remove, not empty: {0}".format(path))
    else:
        log.warn("Cannot remove, unknown reason: {0}".format(path))




# backwards compatibility for conda-build
prefix_placeholder = PREFIX_PLACEHOLDER






def mk_menus(prefix, files, remove=False):
    """
    Create cross-platform menu items (e.g. Windows Start Menu)

    Passes all menu config files %PREFIX%/Menu/*.json to ``menuinst.install``.
    ``remove=True`` will remove the menu items.
    """
    menu_files = [f for f in files
                  if (f.lower().startswith('menu/') and
                      f.lower().endswith('.json'))]
    if not menu_files:
        return
    elif basename(abspath(prefix)).startswith('_'):
        logging.warn("Environment name starts with underscore '_'.  "
                     "Skipping menu installation.")
        return

    try:
        import menuinst
    except:
        logging.warn("Menuinst could not be imported:")
        logging.warn(traceback.format_exc())
        return

    for f in menu_files:
        try:
            menuinst.install(join(prefix, f), remove, prefix)
        except:
            stdoutlog.error("menuinst Exception:")
            stdoutlog.error(traceback.format_exc())



# Should this be an API function?
def symlink_conda(prefix, root_dir, shell=None):
    # do not symlink root env - this clobbers activate incorrectly.
    # prefix should always be longer than, or outside the root dir.
    if normcase(normpath(prefix)) in normcase(normpath(root_dir)):
        return
    if on_win:
        where = 'Scripts'
        symlink_fn = functools.partial(win_conda_bat_redirect, shell=shell)
    else:
        where = 'bin'
        symlink_fn = os.symlink
    if not isdir(join(prefix, where)):
        os.makedirs(join(prefix, where))
    symlink_conda_hlp(prefix, root_dir, where, symlink_fn)


def symlink_conda_hlp(prefix, root_dir, where, symlink_fn):
    scripts = ["conda", "activate", "deactivate"]
    prefix_where = join(prefix, where)
    if not isdir(prefix_where):
        os.makedirs(prefix_where)
    for f in scripts:
        root_file = join(root_dir, where, f)
        prefix_file = join(prefix_where, f)
        try:
            # try to kill stale links if they exist
            if os.path.lexists(prefix_file):
                rm_rf(prefix_file)
            # if they're in use, they won't be killed.  Skip making new symlink.
            if not os.path.lexists(prefix_file):
                symlink_fn(root_file, prefix_file)
        except (IOError, OSError) as e:
            if (os.path.lexists(prefix_file) and
                    (e.errno in (errno.EPERM, errno.EACCES, errno.EROFS, errno.EEXIST))):
                log.debug("Cannot symlink {0} to {1}. Ignoring since link already exists."
                          .format(root_file, prefix_file))
            else:
                raise


# ========================== begin API functions =========================

def try_hard_link(pkgs_dir, prefix, dist):
    # TODO: Usage of this function is bad all around it looks like

    dist = Dist(dist)
    src = join(pkgs_dir, dist.dist_name, 'info', 'index.json')
    dst = join(prefix, '.tmp-%s' % dist.dist_name)
    assert isfile(src), src
    assert not isfile(dst), dst
    try:
        if not isdir(prefix):
            os.makedirs(prefix)
        _link(src, dst, LINK_HARD)
        # Some file systems (at least BeeGFS) do not support hard-links
        # between files in different directories. Depending on the
        # file system configuration, a symbolic link may be created
        # instead. If a symbolic link is created instead of a hard link,
        # return False.
        return not os.path.islink(dst)
    except OSError:
        return False
    finally:
        rm_rf(dst)



def link(prefix, dist, linktype=LINK_HARD, index=None):
    """
    Set up a package in a specified (environment) prefix.  We assume that
    the package has been extracted (using extract() above).
    """
    log.debug("linking package %s with link type %s", dist, linktype)
    index = index or {}
    source_dir = is_extracted(dist)
    assert source_dir is not None
    pkgs_dir = dirname(source_dir)
    log.debug('pkgs_dir=%r, prefix=%r, dist=%r, linktype=%r', pkgs_dir, prefix, dist, linktype)

    if not run_script(source_dir, dist, 'pre-link', prefix):
        raise LinkError('Error: pre-link failed: %s' % dist)

    info_dir = join(source_dir, 'info')
    files = list(yield_lines(join(info_dir, 'files')))
    has_prefix_files = read_has_prefix(join(info_dir, 'has_prefix'))
    no_link = read_no_link(info_dir)

    # for the lock issue
    # may run into lock if prefix not exist
    if not isdir(prefix):
        os.makedirs(prefix)

    with DirectoryLock(prefix), FileLock(source_dir):
        meta_dict = index.get(dist + '.tar.bz2', {})
        if meta_dict.get('noarch'):
            link_noarch(prefix, meta_dict, source_dir, dist)
        else:
            for filepath in files:
                src = join(source_dir, filepath)
                dst = join(prefix, filepath)
                dst_dir = dirname(dst)
                if not isdir(dst_dir):
                    os.makedirs(dst_dir)
                if os.path.exists(dst):
                    log.info("file exists, but clobbering: %r" % dst)
                    rm_rf(dst)
                lt = linktype
                if filepath in has_prefix_files or filepath in no_link or islink(src):
                    lt = LINK_COPY

                try:
                    if not meta_dict.get('noarch'):
                        _link(src, dst, lt)
                except OSError as e:
                    raise CondaOSError('failed to link (src=%r, dst=%r, type=%r, error=%r)' %
                                       (src, dst, lt, e))

        for filepath in sorted(has_prefix_files):
            placeholder, mode = has_prefix_files[filepath]
            try:
                update_prefix(join(prefix, filepath), prefix, placeholder, mode)
            except _PaddingError:
                raise PaddingError(dist, placeholder, len(placeholder))

        # make sure that the child environment behaves like the parent,
        #    wrt user/system install on win
        # This is critical for doing shortcuts correctly
        if on_win:
            nonadmin = join(sys.prefix, ".nonadmin")
            if isfile(nonadmin):
                open(join(prefix, ".nonadmin"), 'w').close()

        if context.shortcuts:
            mk_menus(prefix, files, remove=False)

        if not run_script(prefix, dist, 'post-link'):
            raise LinkError("Error: post-link failed for: %s" % dist)


        create_meta(prefix, dist, source_dir, index, files, linktype)


def unlink(prefix, dist):
    """
    Remove a package from the specified environment, it is an error if the
    package does not exist in the prefix.
    """
    with DirectoryLock(prefix):
        log.debug("unlinking package %s", dist)
        run_script(prefix, dist, 'pre-unlink')

        meta = load_meta(prefix, dist)
        # Always try to run this - it should not throw errors where menus do not exist
        mk_menus(prefix, meta['files'], remove=True)
        dst_dirs1 = set()

        for f in meta['files']:
            dst = join(prefix, f)
            dst_dirs1.add(dirname(dst))
            rm_rf(dst)

        # remove the meta-file last
        delete_linked_data(prefix, dist, delete=True)

        dst_dirs2 = set()
        for path in dst_dirs1:
            while len(path) > len(prefix):
                dst_dirs2.add(path)
                path = dirname(path)
        # in case there is nothing left
        dst_dirs2.add(join(prefix, 'conda-meta'))
        dst_dirs2.add(prefix)

        noarch = meta.get("noarch")
        if noarch:
            get_noarch_cls(noarch)().unlink(prefix, dist)

        # remove empty directories
        for path in sorted(dst_dirs2, key=len, reverse=True):
            if isdir(path) and not os.listdir(path):
                rm_rf(path)

        alt_files_path = join(prefix, 'conda-meta', dist2filename(dist, '.files'))
        if isfile(alt_files_path):
            rm_rf(alt_files_path)


def messages(prefix):
    path = join(prefix, '.messages.txt')
    try:
        with open(path) as fi:
            fh = sys.stderr if context.json else sys.stdout
            fh.write(fi.read())
    except IOError:
        pass
    finally:
        rm_rf(path)
