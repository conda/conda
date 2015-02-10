# (c) 2012-2014 Continuum Analytics, Inc. / http://continuum.io
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

import time
import os
import json
import shutil
import stat
import sys
import subprocess
import tarfile
import traceback
import logging
import shlex
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
    win_ignore_root = set(['python', 'pycosat', 'psutil'])

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
stdoutlog = logging.getLogger('stdoutlog')

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


def _remove_readonly(func, path, excinfo):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def rm_rf(path, max_retries=5):
    """
    Completely delete path

    max_retries is the number of times to retry on failure. The default is
    5. This only applies to deleting a directory.

    """
    if islink(path) or isfile(path):
        # Note that we have to check if the destination is a link because
        # exists('/path/to/dead-link') will return False, although
        # islink('/path/to/dead-link') is True.
        os.unlink(path)

    elif isdir(path):
        for i in range(max_retries):
            try:
                shutil.rmtree(path)
                return
            except OSError as e:
                msg = "Unable to delete %s\n%s\n" % (path, e)
                if on_win:
                    try:
                        shutil.rmtree(path, onerror=_remove_readonly)
                        return
                    except OSError as e1:
                        msg += "Retry with onerror failed (%s)\n" % e1

                    try:
                        subprocess.check_call(['cmd', '/c', 'rd', '/s', '/q', path])
                        return
                    except subprocess.CalledProcessError as e2:
                        msg += '%s\n' % e2
                log.debug(msg + "Retrying after %s seconds..." % i)
                time.sleep(i)
        # Final time. pass exceptions to caller.
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

def read_has_prefix(path):
    """
    reads `has_prefix` file and return dict mapping filenames to
    tuples(placeholder, mode)
    """
    res = {}
    try:
        for line in yield_lines(path):
            try:
                placeholder, mode, f = [x.strip('"\'') for x in
                                        shlex.split(line, posix=False)]
                res[f] = (placeholder, mode)
            except ValueError:
                res[line] = (prefix_placeholder, 'text')
    except IOError:
        pass
    return res

class PaddingError(Exception):
    pass

def binary_replace(data, a, b):
    """
    Perform a binary replacement of `data`, where the placeholder `a` is
    replaced with `b` and the remaining string is padded with null characters.
    All input arguments are expected to be bytes objects.
    """
    import re

    def replace(match):
        occurances = match.group().count(a)
        padding = (len(a) - len(b))*occurances
        if padding < 0:
            raise PaddingError(a, b, padding)
        return match.group().replace(a, b) + b'\0' * padding
    pat = re.compile(re.escape(a) + b'([^\0]*?)\0')
    res = pat.sub(replace, data)
    assert len(res) == len(data)
    return res

def update_prefix(path, new_prefix, placeholder=prefix_placeholder,
                  mode='text'):
    if on_win and (placeholder != prefix_placeholder) and ('/' in placeholder):
        # original prefix uses unix-style path separators
        # replace with unix-style path separators
        new_prefix = new_prefix.replace('\\', '/')

    path = os.path.realpath(path)
    with open(path, 'rb') as fi:
        data = fi.read()
    if mode == 'text':
        new_data = data.replace(placeholder.encode('utf-8'),
                                new_prefix.encode('utf-8'))
    elif mode == 'binary':
        new_data = binary_replace(data, placeholder.encode('utf-8'),
                                  new_prefix.encode('utf-8'))
    else:
        sys.exit("Invalid mode:" % mode)

    if new_data == data:
        return
    st = os.lstat(path)
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
            stdoutlog.error("menuinst Exception:")
            stdoutlog.error(traceback.format_exc())


def run_script(prefix, dist, action='post-link', env_prefix=None):
    """
    call the post-link (or pre-unlink) script, and return True on success,
    False on failure
    """
    path = join(prefix, 'Scripts' if on_win else 'bin', '.%s-%s.%s' % (
            name_dist(dist),
            action,
            'bat' if on_win else 'sh'))
    if not isfile(path):
        return True
    if on_win:
        try:
            args = [os.environ['COMSPEC'], '/c', path]
        except KeyError:
            return False
    else:
        args = ['/bin/bash', path]
    env = os.environ
    env['PREFIX'] = str(env_prefix or prefix)
    env['PKG_NAME'], env['PKG_VERSION'], env['PKG_BUILDNUM'] = \
                str(dist).rsplit('-', 2)
    if action == 'pre-link':
        env['SOURCE_DIR'] = str(prefix)
    try:
        subprocess.check_call(args, env=env)
    except subprocess.CalledProcessError:
        return False
    return True


def read_url(pkgs_dir, dist):
    try:
        data = open(join(pkgs_dir, 'urls.txt')).read()
        urls = data.split()
        for url in urls[::-1]:
            if url.endswith('/%s.tar.bz2' % dist):
                return url
    except IOError:
        pass
    return None


def read_icondata(source_dir):
    import base64

    try:
        data = open(join(source_dir, 'info', 'icon.png'), 'rb').read()
        return base64.b64encode(data).decode('utf-8')
    except IOError:
        pass
    return None

def read_no_link(info_dir):
    res = set()
    for fn in 'no_link', 'no_softlink':
        try:
            res.update(set(yield_lines(join(info_dir, fn))))
        except IOError:
            pass
    return res

# Should this be an API function?
def symlink_conda(prefix, root_dir):
    root_conda = join(root_dir, 'bin', 'conda')
    root_activate = join(root_dir, 'bin', 'activate')
    root_deactivate = join(root_dir, 'bin', 'deactivate')
    prefix_conda = join(prefix, 'bin', 'conda')
    prefix_activate = join(prefix, 'bin', 'activate')
    prefix_deactivate = join(prefix, 'bin', 'deactivate')
    if not os.path.lexists(join(prefix, 'bin')):
        os.makedirs(join(prefix, 'bin'))
    if not os.path.lexists(prefix_conda):
        os.symlink(root_conda, prefix_conda)
    if not os.path.lexists(prefix_activate):
        os.symlink(root_activate, prefix_activate)
    if not os.path.lexists(prefix_deactivate):
        os.symlink(root_deactivate, prefix_deactivate)

# ========================== begin API functions =========================

def try_hard_link(pkgs_dir, prefix, dist):
    src = join(pkgs_dir, dist, 'info', 'index.json')
    dst = join(prefix, '.tmp-%s' % dist)
    assert isfile(src), src
    assert not isfile(dst), dst
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
    if not isdir(pkgs_dir):
        return set()
    return set(fn[:-8] for fn in os.listdir(pkgs_dir)
               if fn.endswith('.tar.bz2'))

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
    if not isdir(pkgs_dir):
        return set()
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
        if sys.platform.startswith('linux') and os.getuid() == 0:
            # When extracting as root, tarfile will by restore ownership
            # of extracted files.  However, we want root to be the owner
            # (our implementation of --no-same-owner).
            for root, dirs, files in os.walk(path):
                for fn in files:
                    p = join(root, fn)
                    os.lchown(p, 0, 0)

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


def link(pkgs_dir, prefix, dist, linktype=LINK_HARD, index=None):
    '''
    Set up a package in a specified (environment) prefix.  We assume that
    the package has been extracted (using extract() above).
    '''
    index = index or {}
    log.debug('pkgs_dir=%r, prefix=%r, dist=%r, linktype=%r' %
              (pkgs_dir, prefix, dist, linktype))
    if (on_win and abspath(prefix) == abspath(sys.prefix) and
              name_dist(dist) in win_ignore_root):
        # on Windows we have the file lock problem, so don't allow
        # linking or unlinking some packages
        log.warn('Ignored: %s' % dist)
        return

    source_dir = join(pkgs_dir, dist)
    if not run_script(source_dir, dist, 'pre-link', prefix):
        sys.exit('Error: pre-link failed: %s' % dist)

    info_dir = join(source_dir, 'info')
    files = list(yield_lines(join(info_dir, 'files')))
    has_prefix_files = read_has_prefix(join(info_dir, 'has_prefix'))
    no_link = read_no_link(info_dir)

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
            if f in has_prefix_files or f in no_link or islink(src):
                lt = LINK_COPY
            try:
                _link(src, dst, lt)
            except OSError as e:
                log.error('failed to link (src=%r, dst=%r, type=%r, error=%r)' %
                          (src, dst, lt, e))

        if name_dist(dist) == '_cache':
            return

        for f in sorted(has_prefix_files):
            placeholder, mode = has_prefix_files[f]
            try:
                update_prefix(join(prefix, f), prefix, placeholder, mode)
            except PaddingError:
                sys.exit("ERROR: placeholder '%s' too short in: %s\n" %
                         (placeholder, dist))

        mk_menus(prefix, files, remove=False)

        if not run_script(prefix, dist, 'post-link'):
            sys.exit("Error: post-link failed for: %s" % dist)

        # Make sure the script stays standalone for the installer
        try:
            from conda.config import remove_binstar_tokens
        except ImportError:
            # There won't be any binstar tokens in the installer anyway
            def remove_binstar_tokens(url):
                return url

        meta_dict = index.get(dist + '.tar.bz2', {})
        meta_dict['url'] = read_url(pkgs_dir, dist)
        if meta_dict['url']:
            meta_dict['url'] = remove_binstar_tokens(meta_dict['url'])
        try:
            alt_files_path = join(prefix, 'conda-meta', dist + '.files')
            meta_dict['files'] = list(yield_lines(alt_files_path))
            os.unlink(alt_files_path)
        except IOError:
            meta_dict['files'] = files
        meta_dict['link'] = {'source': source_dir,
                             'type': link_name_map.get(linktype)}
        if 'channel' in meta_dict:
            meta_dict['channel'] = remove_binstar_tokens(meta_dict['channel'])
        if 'icon' in meta_dict:
            meta_dict['icondata'] = read_icondata(source_dir)

        create_meta(prefix, dist, info_dir, meta_dict)

def unlink(prefix, dist):
    '''
    Remove a package from the specified environment, it is an error if the
    package does not exist in the prefix.
    '''
    if (on_win and abspath(prefix) == abspath(sys.prefix) and
              name_dist(dist) in win_ignore_root):
        # on Windows we have the file lock problem, so don't allow
        # linking or unlinking some packages
        log.warn('Ignored: %s' % dist)
        return

    with Locked(prefix):
        run_script(prefix, dist, 'pre-unlink')

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

    if opts.list:
        pprint(sorted(linked(prefix)))

    elif opts.link_all:
        dists = sorted(extracted(pkgs_dir))
        linktype = (LINK_HARD
                    if try_hard_link(pkgs_dir, prefix, dists[0]) else
                    LINK_COPY)
        if opts.verbose or linktype == LINK_COPY:
            print("linktype: %s" % link_name_map[linktype])
        for dist in dists:
            if opts.verbose or linktype == LINK_COPY:
                print("linking: %s" % dist)
            link(pkgs_dir, prefix, dist, linktype)
        messages(prefix)

    elif opts.extract:
        extract(pkgs_dir, dist)

    elif opts.link:
        link(pkgs_dir, prefix, dist)

    elif opts.unlink:
        unlink(prefix, dist)


if __name__ == '__main__':
    main()
