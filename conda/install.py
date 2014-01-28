# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
''' This module contains:
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

Also, this module is directly invoked by the (self extracting (sfx)) tarball
installer to create the initial environment, therefore it needs to be
standalone, i.e. not import any other parts of `conda` (only depend on
the standard library).

'''

from __future__ import print_function, division, absolute_import

import os
import json
import shutil
import stat
import sys
import subprocess
import tarfile
import traceback
import logging
from os.path import abspath, basename, dirname, isdir, isfile, islink, join

try:
    from conda.lock import Locked
except ImportError:
    # Make sure this still works as a standalone script for the Anaconda
    # installer.
    class Locked(object):
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            pass
        def __exit__(self, exc_type, exc_value, traceback):
            pass

on_win = bool(sys.platform == 'win32')

if on_win:
    import ctypes
    from ctypes import wintypes

    # on Windows we cannot update these packages in the root environment
    # because of the file lock problem
    win_ignore_root = set(['python', 'pycosat', 'menuinst', 'psutil'])

    CreateHardLink = ctypes.windll.kernel32.CreateHardLinkW
    CreateHardLink.restype = wintypes.BOOL
    CreateHardLink.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR,
                               wintypes.LPVOID]
    try:
        CreateSymbolicLink = ctypes.windll.kernel32.CreateSymbolicLinkW
        CreateSymbolicLink.restype = wintypes.BOOL
        CreateSymbolicLink.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR,
                                       wintypes.DWORD]
    except AttributeError:
        CreateSymbolicLink = None

    def win_hard_link(src, dst):
        "Equivalent to os.link, using the win32 CreateHardLink call."
        if not CreateHardLink(dst, src, None):
            raise OSError('win32 hard link failed')

    def win_soft_link(src, dst):
        "Equivalent to os.symlink, using the win32 CreateSymbolicLink call."
        if CreateSymbolicLink is None:
            raise OSError('win32 soft link not supported')
        if not CreateSymbolicLink(dst, src, isdir(src)):
            raise OSError('win32 soft link failed')


log = logging.getLogger(__name__)

class NullHandler(logging.Handler):
    """ Copied from Python 2.7 to avoid getting
        `No handlers could be found for logger "patch"`
        http://bugs.python.org/issue16539
    """
    def handle(self, record):
        pass
    def emit(self, record):
        pass
    def createLock(self):
        self.lock = None

log.addHandler(NullHandler())

LINK_HARD = 1
LINK_SOFT = 2
LINK_COPY = 3
link_name_map = {
    LINK_HARD: 'hard-link',
    LINK_SOFT: 'soft-link',
    LINK_COPY: 'copy',
}

def _link(src, dst, linktype=LINK_HARD):
    if linktype == LINK_HARD:
        if on_win:
            win_hard_link(src, dst)
        else:
            os.link(src, dst)
    elif linktype == LINK_SOFT:
        if on_win:
            win_soft_link(src, dst)
        else:
            os.symlink(src, dst)
    elif linktype == LINK_COPY:
        # copy relative symlinks as symlinks
        if not on_win and islink(src) and not os.readlink(src).startswith('/'):
            os.symlink(os.readlink(src), dst)
        else:
            shutil.copy2(src, dst)
    else:
        raise Exception("Did not expect linktype=%r" % linktype)


def rm_rf(path):
    if islink(path) or isfile(path):
        # Note that we have to check if the destination is a link because
        # exists('/path/to/dead-link') will return False, although
        # islink('/path/to/dead-link') is True.
        os.unlink(path)

    elif isdir(path):
        shutil.rmtree(path)

def rm_empty_dir(path):
    """
    Remove the directory `path` if it is a directory and empty.
    If the directory does not exist or is not empty, do nothing.
    """
    try:
        os.rmdir(path)
    except OSError: # directory might not exist or not be empty
        pass


def yield_lines(path):
    for line in open(path):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        yield line


prefix_placeholder = ('/opt/anaconda1anaconda2'
                      # this is intentionally split into parts,
                      # such that running this program on itself
                      # will leave it unchanged
                      'anaconda3')
def update_prefix(path, new_prefix):
    path = os.path.realpath(path)
    with open(path, 'rb') as fi:
        data = fi.read()
    new_data = data.replace(prefix_placeholder.encode('utf-8'),
                            new_prefix.encode('utf-8'))
    if new_data == data:
        return
    st = os.lstat(path)
    os.unlink(path)
    with open(path, 'wb') as fo:
        fo.write(new_data)
    os.chmod(path, stat.S_IMODE(st.st_mode))


def name_dist(dist):
    return dist.rsplit('-', 2)[0]


def create_meta(prefix, dist, info_dir, extra_info):
    """
    Create the conda metadata, in a given prefix, for a given package.
    """
    # read info/index.json first
    with open(join(info_dir, 'index.json')) as fi:
        meta = json.load(fi)
    # add extra info
    meta.update(extra_info)
    # write into <env>/conda-meta/<dist>.json
    meta_dir = join(prefix, 'conda-meta')
    if not isdir(meta_dir):
        os.makedirs(meta_dir)
    with open(join(meta_dir, dist + '.json'), 'w') as fo:
        json.dump(meta, fo, indent=2, sort_keys=True)


def mk_menus(prefix, files, remove=False):
    if abspath(prefix) != abspath(sys.prefix):
        # we currently only want to create menu items for packages
        # in default environment
        return
    menu_files = [f for f in files
                  if f.startswith('Menu/') and f.endswith('.json')]
    if not menu_files:
        return
    try:
        import menuinst
    except ImportError:
        return
    for f in menu_files:
        try:
            menuinst.install(join(prefix, f), remove, prefix)
        except:
            print("menuinst Exception:")
            traceback.print_exc(file=sys.stdout)


def post_link(prefix, dist, unlink=False):
    path = join(prefix, 'Scripts' if on_win else 'bin', '.%s-%s.%s' % (
            name_dist(dist),
            'pre-unlink' if unlink else 'post-link',
            'bat' if on_win else 'sh'))
    if not isfile(path):
        return
    if on_win:
        args = [os.environ['COMSPEC'], '/c', path]
    else:
        args = ['/bin/bash', path]
    env = os.environ
    env['PREFIX'] = prefix
    env['PKG_NAME'], env['PKG_VERSION'], unused_build = str(dist).rsplit('-', 2)
    try:
        subprocess.check_call(args, env=env)
    except subprocess.CalledProcessError:
        return False
    return True


# ========================== begin API functions =========================

def try_write(dir_path):
    path = join(dir_path, '.conda-try-write')
    assert isdir(dir_path)
    assert not isfile(path)
    try:
        with open(path, 'wb') as fo:
            fo.write(b'This is a test file.\n')
        return True
    except IOError:
        return False
    finally:
        rm_rf(path)

def try_hard_link(pkgs_dir, prefix, dist):
    src = join(pkgs_dir, dist, 'info', 'index.json')
    dst = join(prefix, '.tmp-%s' % dist)
    assert isfile(src)
    assert not isfile(dst)
    if not isdir(prefix):
        os.makedirs(prefix)
    try:
        _link(src, dst, LINK_HARD)
        return True
    except OSError:
        return False
    finally:
        rm_rf(dst)
        rm_empty_dir(prefix)

# ------- package cache ----- fetched

def fetched(pkgs_dir):
    if isdir(pkgs_dir):
        return set(fn[:-8] for fn in os.listdir(pkgs_dir)
                   if fn.endswith('.tar.bz2'))
    else:
        return set()

def is_fetched(pkgs_dir, dist):
    return isfile(join(pkgs_dir, dist + '.tar.bz2'))

def rm_fetched(pkgs_dir, dist):
    with Locked(pkgs_dir):
        path = join(pkgs_dir, dist + '.tar.bz2')
        rm_rf(path)

# ------- package cache ----- extracted

def extracted(pkgs_dir):
    """
    return the (set of canonical names) of all extracted packages
    """
    return set(dn for dn in os.listdir(pkgs_dir)
               if (isfile(join(pkgs_dir, dn, 'info', 'files')) and
                   isfile(join(pkgs_dir, dn, 'info', 'index.json'))))

def extract(pkgs_dir, dist):
    """
    Extract a package, i.e. make a package available for linkage.  We assume
    that the compressed packages is located in the packages directory.
    """
    with Locked(pkgs_dir):
        path = join(pkgs_dir, dist)
        t = tarfile.open(path + '.tar.bz2')
        t.extractall(path=path)
        t.close()

def is_extracted(pkgs_dir, dist):
    return (isfile(join(pkgs_dir, dist, 'info', 'files')) and
            isfile(join(pkgs_dir, dist, 'info', 'index.json')))

def rm_extracted(pkgs_dir, dist):
    with Locked(pkgs_dir):
        path = join(pkgs_dir, dist)
        rm_rf(path)

# ------- linkage of packages

def linked(prefix):
    """
    Return the (set of canonical names) of linked packages in prefix.
    """
    meta_dir = join(prefix, 'conda-meta')
    if not isdir(meta_dir):
        return set()
    return set(fn[:-5] for fn in os.listdir(meta_dir) if fn.endswith('.json'))


def is_linked(prefix, dist):
    """
    Return the install meta-data for a linked package in a prefix, or None
    if the package is not linked in the prefix.
    """
    meta_path = join(prefix, 'conda-meta', dist + '.json')
    try:
        with open(meta_path) as fi:
            return json.load(fi)
    except IOError:
        return None


def link(pkgs_dir, prefix, dist, linktype=LINK_HARD):
    '''
    Set up a packages in a specified (environment) prefix.  We assume that
    the packages has been extracted (using extract() above).
    '''
    log.debug('pkgs_dir=%r, prefix=%r, dist=%r, linktype=%r' %
              (pkgs_dir, prefix, dist, linktype))
    if (on_win and abspath(prefix) == abspath(sys.prefix) and
              name_dist(dist) in win_ignore_root):
        # on Windows we have the file lock problem, so don't allow
        # linking or unlinking some packages
        print('Ignored: %s' % dist)
        return

    source_dir = join(pkgs_dir, dist)
    info_dir = join(source_dir, 'info')
    files = list(yield_lines(join(info_dir, 'files')))

    try:
        has_prefix_files = set(yield_lines(join(info_dir, 'has_prefix')))
    except IOError:
        has_prefix_files = set()

    if linktype == LINK_SOFT:
        try:
            no_softlink = set(yield_lines(join(info_dir, 'no_softlink')))
        except IOError:
            no_softlink = set()

    with Locked(prefix), Locked(pkgs_dir):
        for f in files:
            src = join(source_dir, f)
            dst = join(prefix, f)
            dst_dir = dirname(dst)
            if not isdir(dst_dir):
                os.makedirs(dst_dir)
            if os.path.exists(dst):
                log.warn("file already exists: %r" % dst)
                try:
                    os.unlink(dst)
                except OSError:
                    log.error('failed to unlink: %r' % dst)
            lt = linktype
            if (f in has_prefix_files or
                    (linktype == LINK_SOFT and f in no_softlink) or
                    islink(src)):
                lt = LINK_COPY
            try:
                _link(src, dst, lt)
            except OSError:
                log.error('failed to link (src=%r, dst=%r, type=%r)' %
                          (src, dst, lt))

        if name_dist(dist) == '_cache':
            return

        for f in sorted(has_prefix_files):
            update_prefix(join(prefix, f), prefix)

        mk_menus(prefix, files, remove=False)

        if not post_link(prefix, dist):
            return

        create_meta(prefix, dist, info_dir, {
                'files': files,
                'link': {'source': source_dir,
                         'type': link_name_map.get(linktype)},
                })


def unlink(prefix, dist):
    '''
    Remove a package from the specified environment, it is an error if the
    package does not exist in the prefix.
    '''
    if (on_win and abspath(prefix) == abspath(sys.prefix) and
              name_dist(dist) in win_ignore_root):
        # on Windows we have the file lock problem, so don't allow
        # linking or unlinking some packages
        print('Ignored: %s' % dist)
        return

    with Locked(prefix):
        post_link(prefix, dist, unlink=True)

        meta_path = join(prefix, 'conda-meta', dist + '.json')
        with open(meta_path) as fi:
            meta = json.load(fi)

        mk_menus(prefix, meta['files'], remove=True)
        dst_dirs1 = set()

        for f in meta['files']:
            dst = join(prefix, f)
            dst_dirs1.add(dirname(dst))
            try:
                os.unlink(dst)
            except OSError: # file might not exist
                log.debug("could not remove file: '%s'" % dst)

        # remove the meta-file last
        os.unlink(meta_path)

        dst_dirs2 = set()
        for path in dst_dirs1:
            while len(path) > len(prefix):
                dst_dirs2.add(path)
                path = dirname(path)
        # in case there is nothing left
        dst_dirs2.add(join(prefix, 'conda-meta'))
        dst_dirs2.add(prefix)

        for path in sorted(dst_dirs2, key=len, reverse=True):
            rm_empty_dir(path)


def messages(prefix):
    path = join(prefix, '.messages.txt')
    try:
        with open(path) as fi:
            sys.stdout.write(fi.read())
    except IOError:
        pass
    finally:
        rm_rf(path)

# =========================== end API functions ==========================

def main():
    from pprint import pprint
    from optparse import OptionParser

    p = OptionParser(
        usage="usage: %prog [options] [TARBALL/NAME]",
        description="low-level conda install tool, by default extracts "
                    "(if necessary) and links a TARBALL")

    p.add_option('-l', '--list',
                 action="store_true",
                 help="list all linked packages")

    p.add_option('--extract',
                 action="store_true",
                 help="extract package in pkgs cache")

    p.add_option('--link',
                 action="store_true",
                 help="link a package")

    p.add_option('--unlink',
                 action="store_true",
                 help="unlink a package")

    p.add_option('-p', '--prefix',
                 action="store",
                 default=sys.prefix,
                 help="prefix (defaults to %default)")

    p.add_option('--pkgs-dir',
                 action="store",
                 default=join(sys.prefix, 'pkgs'),
                 help="packages directory (defaults to %default)")

    p.add_option('--link-all',
                 action="store_true",
                 help="link all extracted packages")

    p.add_option('-v', '--verbose',
                 action="store_true")

    opts, args = p.parse_args()

    logging.basicConfig()

    if opts.list or opts.extract or opts.link_all:
        if args:
            p.error('no arguments expected')
    else:
        if len(args) == 1:
            dist = basename(args[0])
            if dist.endswith('.tar.bz2'):
                dist = dist[:-8]
        else:
            p.error('exactly one argument expected')

    pkgs_dir = opts.pkgs_dir
    prefix = opts.prefix
    if opts.verbose:
        print("pkgs_dir: %r" % pkgs_dir)
        print("prefix  : %r" % prefix)
        print("dist    : %r" % dist)

    if opts.list:
        pprint(sorted(linked(prefix)))

    elif opts.link_all:
        for dist in sorted(extracted(pkgs_dir)):
            link(pkgs_dir, prefix, dist)
        messages(prefix)

    elif opts.extract:
        extract(pkgs_dir, dist)

    elif opts.link:
        link(pkgs_dir, prefix, dist)

    elif opts.unlink:
        unlink(prefix, dist)


if __name__ == '__main__':
    main()
