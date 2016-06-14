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

Also, this module is directly invoked by the (self extracting (sfx)) tarball
installer to create the initial environment, therefore it needs to be
standalone, i.e. not import any other parts of `conda` (only depend on
the standard library).
"""

from __future__ import print_function, division, absolute_import

import errno
import functools
import json
import logging
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tarfile
import time
import traceback
import random
from os.path import (abspath, basename, dirname, isdir, isfile, islink,
                     join, relpath, normpath)

on_win = bool(sys.platform == "win32")

try:
    from conda.lock import Locked
    from conda.utils import win_path_to_unix, url_path
    from conda.config import remove_binstar_tokens, pkgs_dirs, url_channel
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

    def win_path_to_unix(path, root_prefix=""):
        """Convert a path or ;-separated string of paths into a unix representation

        Does not add cygdrive.  If you need that, set root_prefix to "/cygdrive"
        """
        path_re = '(?<![:/^a-zA-Z])([a-zA-Z]:[\/\\\\]+(?:[^:*?"<>|]+[\/\\\\]+)*[^:*?"<>|;\/\\\\]+?(?![a-zA-Z]:))'  # noqa

        def translation(found_path):
            found = found_path.group(1).replace("\\", "/").replace(":", "")
            return root_prefix + "/" + found
        return re.sub(path_re, translation, path).replace(";/", ":/")

    def url_path(path):
        path = abspath(path)
        if on_win:
            path = '/' + path.replace(':', '|').replace('\\', '/')
        return 'file://%s' % path

    # There won't be any binstar tokens in the installer anyway
    def remove_binstar_tokens(url):
        return url

    # A simpler version of url_channel will do
    def url_channel(url):
        return url.rsplit('/', 2)[0] + '/' if url and '/' in url else None, 'defaults'

    pkgs_dirs = [join(sys.prefix, 'pkgs')]

if on_win:
    import ctypes
    from ctypes import wintypes

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

    def win_conda_bat_redirect(src, dst, shell):
        """Special function for Windows XP where the `CreateSymbolicLink`
        function is not available.

        Simply creates a `.bat` file at `dst` which calls `src` together with
        all command line arguments.

        Works of course only with callable files, e.g. `.bat` or `.exe` files.
        """
        from conda.utils import shells
        try:
            os.makedirs(os.path.dirname(dst))
        except OSError as exc:  # Python >2.5
            if exc.errno == errno.EEXIST and os.path.isdir(os.path.dirname(dst)):
                pass
            else:
                raise

        if 'cmd.exe' in shell.lower():
            # bat file redirect
            with open(dst+'.bat', 'w') as f:
                f.write('@echo off\n"%s" %%*\n' % src)

        elif 'powershell' in shell.lower():
            # TODO: probably need one here for powershell at some point
            pass

        else:
            # This one is for bash/cygwin/msys
            with open(dst, "w") as f:
                f.write("#!/usr/bin/env bash \n")
                if src.endswith("conda"):
                    f.write('%s "$@"' % shells[shell]['path_to'](src+".exe"))
                else:
                    f.write('source %s "$@"' % shells[shell]['path_to'](src))
            # Make the new file executable
            # http://stackoverflow.com/a/30463972/1170370
            mode = os.stat(dst).st_mode
            mode |= (mode & 292) >> 2    # copy R bits to X
            os.chmod(dst, mode)

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

def warn_failed_remove(function, path, exc_info):
    if exc_info[1].errno == errno.EACCES:
        log.warn("Cannot remove, permission denied: {0}".format(path))
    elif exc_info[1].errno == errno.ENOTEMPTY:
        log.warn("Cannot remove, not empty: {0}".format(path))
    else:
        log.warn("Cannot remove, unknown reason: {0}".format(path))


def exp_backoff_fn(fn, *args):
    """Mostly for retrying file operations that fail on Windows due to virus scanners"""
    max_retries = 5
    for n in range(max_retries):
        try:
            result = fn(*args)
        except Exception as e:
            log.debug(repr(e))
            if n == max_retries-1:
                raise
            time.sleep((2 ** n) + (random.randint(0, 1000) / 1000))
        else:
            return result


def rm_rf(path, max_retries=5, trash=True):
    """
    Completely delete path

    max_retries is the number of times to retry on failure. The default is
    5. This only applies to deleting a directory.

    If removing path fails and trash is True, files will be moved to the trash directory.
    """
    if islink(path) or isfile(path):
        # Note that we have to check if the destination is a link because
        # exists('/path/to/dead-link') will return False, although
        # islink('/path/to/dead-link') is True.
        try:
            os.unlink(path)
        except (OSError, IOError):
            log.warn("Cannot remove, permission denied: {0}".format(path))

    elif isdir(path):
        try:
            for i in range(max_retries):
                try:
                    shutil.rmtree(path, ignore_errors=False, onerror=warn_failed_remove)
                    return
                except OSError as e:
                    msg = "Unable to delete %s\n%s\n" % (path, e)
                    if on_win:
                        try:
                            shutil.rmtree(path, onerror=_remove_readonly)
                            return
                        except OSError as e1:
                            msg += "Retry with onerror failed (%s)\n" % e1

                        p = subprocess.Popen(['cmd', '/c', 'rd', '/s', '/q', path],
                                             stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE)
                        (stdout, stderr) = p.communicate()
                        if p.returncode != 0:
                            msg += '%s\n%s\n' % (stdout, stderr)
                        else:
                            if not isdir(path):
                                return

                        if trash:
                            try:
                                move_path_to_trash(path)
                                if not isdir(path):
                                    return
                            except OSError as e2:
                                raise
                                msg += "Retry with onerror failed (%s)\n" % e2

                    log.debug(msg + "Retrying after %s seconds..." % i)
                    time.sleep(i)
            # Final time. pass exceptions to caller.
            shutil.rmtree(path, ignore_errors=False, onerror=warn_failed_remove)
        finally:
            # If path was removed, ensure it's not in linked_data_
            if not isdir(path):
                delete_linked_data_any(path)

def rm_empty_dir(path):
    """
    Remove the directory `path` if it is a directory and empty.
    If the directory does not exist or is not empty, do nothing.
    """
    try:
        os.rmdir(path)
    except OSError:  # directory might not exist or not be empty
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


def replace_long_shebang(mode, data):
    if mode == 'text':
        shebang_match = re.match(br'^(#!((?:\\ |[^ \n\r])+)(.*))', data)
        if shebang_match:
            whole_shebang, executable, options = shebang_match.groups()
            if len(whole_shebang) > 127:
                executable_name = executable.decode('utf-8').split('/')[-1]
                new_shebang = '#!/usr/bin/env {0}{1}'.format(executable_name,
                                                             options.decode('utf-8'))
                data = data.replace(whole_shebang, new_shebang.encode('utf-8'))
    else:
        pass  # TODO: binary shebangs exist; figure this out in the future if text works well
    return data


def replace_prefix(mode, data, placeholder, new_prefix):
    if mode == 'text':
        data = data.replace(placeholder.encode('utf-8'), new_prefix.encode('utf-8'))
    # Skip binary replacement in Windows.  Some files do have prefix information embedded, but
    #    this should not matter, as it is not used for things like RPATH.
    elif mode == 'binary':
        if not on_win:
            data = binary_replace(data, placeholder.encode('utf-8'), new_prefix.encode('utf-8'))
        else:
            logging.debug("Skipping prefix replacement in binary on Windows")
    else:
        sys.exit("Invalid mode: %s" % mode)
    return data


def update_prefix(path, new_prefix, placeholder=prefix_placeholder, mode='text'):
    if on_win:
        # force all prefix replacements to forward slashes to simplify need to escape backslashes
        # replace with unix-style path separators
        new_prefix = new_prefix.replace('\\', '/')

    path = os.path.realpath(path)
    with open(path, 'rb') as fi:
        original_data = data = fi.read()

    data = replace_prefix(mode, data, placeholder, new_prefix)
    if not on_win:
        data = replace_long_shebang(mode, data)

    if data == original_data:
        return
    st = os.lstat(path)
    # Remove file before rewriting to avoid destroying hard-linked cache
    os.remove(path)
    with exp_backoff_fn(open, path, 'wb') as fo:
        fo.write(data)
    os.chmod(path, stat.S_IMODE(st.st_mode))


def dist2pair(dist):
    dist = str(dist)
    if dist.endswith(']'):
        dist = dist.split('[', 1)[0]
    if dist.endswith('.tar.bz2'):
        dist = dist[:-8]
    parts = dist.split('::', 1)
    return 'defaults' if len(parts) < 2 else parts[0], parts[-1]


def dist2quad(dist):
    channel, dist = dist2pair(dist)
    parts = dist.rsplit('-', 2) + ['', '']
    return (parts[0], parts[1], parts[2], channel)


def dist2name(dist):
    return dist2quad(dist)[0]


def name_dist(dist):
    return dist2name(dist)


def dist2filename(dist, suffix='.tar.bz2'):
    return dist2pair(dist)[1] + suffix


def dist2dirname(dist):
    return dist2filename(dist, '')


def create_meta(prefix, dist, info_dir, extra_info):
    """
    Create the conda metadata, in a given prefix, for a given package.
    """
    # read info/index.json first
    with open(join(info_dir, 'index.json')) as fi:
        meta = json.load(fi)
    # add extra info, add to our intenral cache
    meta.update(extra_info)
    if 'url' not in meta:
        meta['url'] = read_url(dist)
    # write into <env>/conda-meta/<dist>.json
    meta_dir = join(prefix, 'conda-meta')
    if not isdir(meta_dir):
        os.makedirs(meta_dir)
    with open(join(meta_dir, dist2filename(dist, '.json')), 'w') as fo:
        json.dump(meta, fo, indent=2, sort_keys=True)
    if prefix in linked_data_:
        load_linked_data(prefix, dist, meta)


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
        shell_path = '/bin/sh' if 'bsd' in sys.platform else '/bin/bash'
        args = [shell_path, path]
    env = os.environ
    env['ROOT_PREFIX'] = sys.prefix
    env['PREFIX'] = str(env_prefix or prefix)
    env['PKG_NAME'], env['PKG_VERSION'], env['PKG_BUILDNUM'], _ = dist2quad(dist)
    if action == 'pre-link':
        env['SOURCE_DIR'] = str(prefix)
    try:
        subprocess.check_call(args, env=env)
    except subprocess.CalledProcessError:
        return False
    return True


def read_url(dist):
    res = package_cache().get(dist, {}).get('urls', (None,))
    return res[0] if res else None


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
def symlink_conda(prefix, root_dir, shell):
    # do not symlink root env - this clobbers activate incorrectly.
    if normpath(prefix) == normpath(sys.prefix):
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
                os.remove(prefix_file)
            # if they're in use, they won't be killed.  Skip making new symlink.
            if not os.path.lexists(prefix_file):
                symlink_fn(root_file, prefix_file)
        except (IOError, OSError) as e:
            if (os.path.lexists(prefix_file) and
                    (e.errno == errno.EPERM or e.errno == errno.EACCES)):
                log.debug("Cannot symlink {0} to {1}. Ignoring since link already exists."
                          .format(root_file, prefix_file))
            else:
                raise

# ========================== begin API functions =========================

def try_hard_link(pkgs_dir, prefix, dist):
    dist = dist2filename(dist, '')
    src = join(pkgs_dir, dist, 'info', 'index.json')
    dst = join(prefix, '.tmp-%s' % dist)
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
        rm_empty_dir(prefix)

# ------- package cache ----- construction

# The current package cache does not support the ability to store multiple packages
# with the same filename from different channels. Furthermore, the filename itself
# cannot be used to disambiguate; we must read the URL from urls.txt to determine
# the source channel. For this reason, we now fully parse the directory and its
# accompanying urls.txt file so we can make arbitrary queries without having to
# read this data multiple times.

package_cache_ = {}
fname_table_ = {}


def add_cached_package(pdir, url, overwrite=False, urlstxt=False):
    """
    Adds a new package to the cache. The URL is used to determine the
    package filename and channel, and the directory pdir is scanned for
    both a compressed and an extracted version of that package. If
    urlstxt=True, this URL will be appended to the urls.txt file in the
    cache, so that subsequent runs will correctly identify the package.
    """
    package_cache()
    if '/' in url:
        dist = url.rsplit('/', 1)[-1]
    else:
        dist = url
        url = None
    if dist.endswith('.tar.bz2'):
        fname = dist
        dist = dist[:-8]
    else:
        fname = dist + '.tar.bz2'
    xpkg = join(pdir, fname)
    if not overwrite and xpkg in fname_table_:
        return
    if not isfile(xpkg):
        xpkg = None
    xdir = join(pdir, dist)
    if not (isdir(xdir) and
            isfile(join(xdir, 'info', 'files')) and
            isfile(join(xdir, 'info', 'index.json'))):
        xdir = None
    if not (xpkg or xdir):
        return
    if url:
        url = remove_binstar_tokens(url)
    _, schannel = url_channel(url)
    prefix = '' if schannel == 'defaults' else schannel + '::'
    xkey = xpkg or (xdir + '.tar.bz2')
    fname_table_[xkey] = fname_table_[url_path(xkey)] = prefix
    fkey = prefix + dist
    rec = package_cache_.get(fkey)
    if rec is None:
        rec = package_cache_[fkey] = dict(files=[], dirs=[], urls=[])
    if url and url not in rec['urls']:
        rec['urls'].append(url)
    if xpkg and xpkg not in rec['files']:
        rec['files'].append(xpkg)
    if xdir and xdir not in rec['dirs']:
        rec['dirs'].append(xdir)
    if urlstxt:
        try:
            with open(join(pdir, 'urls.txt'), 'a') as fa:
                fa.write('%s\n' % url)
        except IOError:
            pass


def package_cache():
    """
    Initializes the package cache. Each entry in the package cache
    dictionary contains three lists:
    - urls: the URLs used to refer to that package
    - files: the full pathnames to fetched copies of that package
    - dirs: the full pathnames to extracted copies of that package
    Nominally there should be no more than one entry in each list, but
    in theory this can handle the presence of multiple copies.
    """
    if package_cache_:
        return package_cache_
    # Stops recursion
    package_cache_['@'] = None
    for pdir in pkgs_dirs:
        try:
            data = open(join(pdir, 'urls.txt')).read()
            for url in data.split()[::-1]:
                if '/' in url:
                    add_cached_package(pdir, url)
        except IOError:
            pass
        if isdir(pdir):
            for fn in os.listdir(pdir):
                add_cached_package(pdir, fn)
    del package_cache_['@']
    return package_cache_


def cached_url(url):
    package_cache()
    return fname_table_.get(url)


def find_new_location(dist):
    """
    Determines the download location for the given package, and the name
    of a package, if any, that must be removed to make room. If the
    given package is already in the cache, it returns its current location,
    under the assumption that it will be overwritten. If the conflict
    value is None, that means there is no other package with that same
    name present in the cache (e.g., no collision).
    """
    rec = package_cache().get(dist)
    if rec:
        return dirname((rec['files'] or rec['dirs'])[0]), None
    fname = dist2filename(dist)
    dname = fname[:-8]
    # Look for a location with no conflicts
    # On the second pass, just pick the first location
    for p in range(2):
        for pkg_dir in pkgs_dirs:
            pkg_path = join(pkg_dir, fname)
            prefix = fname_table_.get(pkg_path)
            if p or prefix is None:
                return pkg_dir, prefix + dname if p else None


# ------- package cache ----- fetched

def fetched():
    """
    Returns the (set of canonical names) of all fetched packages
    """
    return set(dist for dist, rec in package_cache().items() if rec['files'])


def is_fetched(dist):
    """
    Returns the full path of the fetched package, or None if it is not in the cache.
    """
    for fn in package_cache().get(dist, {}).get('files', ()):
        return fn


def rm_fetched(dist):
    """
    Checks to see if the requested package is in the cache; and if so, it removes both
    the package itself and its extracted contents.
    """

    rec = package_cache().get(dist)
    if rec is None:
        return
    for fname in rec['files']:
        del fname_table_[fname]
        del fname_table_[url_path(fname)]
        with Locked(dirname(fname), dist):
            rm_rf(fname)
    for fname in rec['dirs']:
        with Locked(dirname(fname), dist):
            rm_rf(fname)
    del package_cache_[dist]


# ------- package cache ----- extracted

def extracted():
    """
    return the (set of canonical names) of all extracted packages
    """
    return set(dist for dist, rec in package_cache().items() if rec['dirs'])


def is_extracted(dist):
    """
    returns the full path of the extracted data for the requested package,
    or None if that package is not extracted.
    """
    for fn in package_cache().get(dist, {}).get('dirs', ()):
        return fn


def rm_extracted(dist):
    """
    Removes any extracted versions of the given package found in the cache.
    """
    rec = package_cache().get(dist)
    if rec is None:
        return
    for fname in rec['dirs']:
        with Locked(dirname(fname), dist):
            rm_rf(fname)
    if rec['files']:
        rec['dirs'] = []
    else:
        del package_cache_[dist]


def extract(dist):
    """
    Extract a package, i.e. make a package available for linkage. We assume
    that the compressed package is located in the packages directory.
    """
    rec = package_cache()[dist]
    url = rec['urls'][0]
    fname = rec['files'][0]
    assert url and fname
    pkgs_dir = dirname(fname)
    with Locked(pkgs_dir, dist):
        path = fname[:-8]
        temp_path = path + '.tmp'
        rm_rf(temp_path)
        with tarfile.open(fname) as t:
            t.extractall(path=temp_path)
        rm_rf(path)
        exp_backoff_fn(os.rename, temp_path, path)
        if sys.platform.startswith('linux') and os.getuid() == 0:
            # When extracting as root, tarfile will by restore ownership
            # of extracted files.  However, we want root to be the owner
            # (our implementation of --no-same-owner).
            for root, dirs, files in os.walk(path):
                for fn in files:
                    p = join(root, fn)
                    os.lchown(p, 0, 0)
        add_cached_package(pkgs_dir, url, overwrite=True)

# Because the conda-meta .json files do not include channel names in
# their filenames, we have to pull that information from the .json
# files themselves. This has made it necessary in virtually all
# circumstances to load the full set of files from this directory.
# Therefore, we have implemented a full internal cache of this
# data to eliminate redundant file reads.

linked_data_ = {}


def load_linked_data(prefix, dist, rec=None):
    schannel, dname = dist2pair(dist)
    meta_file = join(prefix, 'conda-meta', dname + '.json')
    if rec is None:
        try:
            with open(meta_file) as fi:
                rec = json.load(fi)
        except IOError as e:
            log.debug("Could not open '%s'" % e)
            raise

    else:
        linked_data(prefix)
    url = rec.get('url')
    if 'fn' not in rec:
        rec['fn'] = url.rsplit('/', 1)[-1] if url else dname + '.tar.bz2'
    if not url and 'channel' in rec:
        url = rec['url'] = rec['channel'] + rec['fn']
    if rec['fn'][:-8] != dname:
        log.debug('Ignoring invalid package metadata file: %s' % meta_file)
        return None
    channel, schannel = url_channel(url)
    rec['channel'] = channel
    rec['schannel'] = schannel
    rec['link'] = rec.get('link') or True
    cprefix = '' if schannel == 'defaults' else schannel + '::'
    linked_data_[prefix][str(cprefix + dname)] = rec
    return rec


def delete_linked_data(prefix, dist, delete=True):
    recs = linked_data_.get(prefix)
    if recs and dist in recs:
        del recs[dist]
    if delete:
        meta_path = join(prefix, 'conda-meta', dist2filename(dist, '.json'))
        if isfile(meta_path):
            os.unlink(meta_path)


def delete_linked_data_any(path):
    '''Here, path may be a complete prefix or a dist inside a prefix'''
    dist = ''
    while True:
        if path in linked_data_:
            if dist:
                delete_linked_data(path, dist)
                return True
            else:
                del linked_data_[path]
                return True
        path, dist = os.path.split(path)
        if not dist:
            return False


def load_meta(prefix, dist):
    """
    Return the install meta-data for a linked package in a prefix, or None
    if the package is not linked in the prefix.
    """
    return linked_data(prefix).get(dist)


def linked_data(prefix):
    """
    Return a dictionary of the linked packages in prefix.
    """
    # Manually memoized so it can be updated
    recs = linked_data_.get(prefix)
    json_files = []
    if recs is None:
        recs = linked_data_[prefix] = {}
        meta_dir = join(prefix, 'conda-meta')
        if isdir(meta_dir):
            for fn in os.listdir(meta_dir):
                if fn.endswith('.json'):
                    json_files.append(fn[:-5])
        try:
            import concurrent.futures
            executor = concurrent.futures.ThreadPoolExecutor(10)
        except (ImportError, RuntimeError):

            # concurrent.futures is only available in Python >= 3.2 or if futures is installed
            # RuntimeError is thrown if number of threads are limited by OS
            for fn in json_files:
                load_linked_data(prefix, fn)
        else:
            try:
                json_files_tuple = tuple(json_files)
                tuple(executor.submit(load_linked_data, prefix,
                                      json_file) for json_file in json_files_tuple)
            finally:
                executor.shutdown(wait=True)
    return recs


def linked(prefix):
    """
    Return the set of canonical names of linked packages in prefix.
    """
    return set(linked_data(prefix).keys())


def is_linked(prefix, dist):
    """
    Return the install metadata for a linked package in a prefix, or None
    if the package is not linked in the prefix.
    """
    # FIXME Functions that begin with `is_` should return True/False
    return load_meta(prefix, dist)


def _get_trash_dir(pkg_dir):
    unc_prefix = u'\\\\?\\' if on_win else ''
    return unc_prefix + join(pkg_dir, '.trash')


def _safe_relpath(path, start_path):
    """
    Used in the move_to_trash flow. Ensures that the result does not
    start with any '..' which would allow to escape the trash folder
    (and root prefix) and potentially ruin the user's system.
    """
    result = normpath(relpath(path, start_path))
    parts = result.rsplit(os.sep)
    for idx, part in enumerate(parts):
        if part != u'..':
            return os.sep.join(parts[idx:])
    return u''


def delete_trash(prefix=None):
    for pkg_dir in pkgs_dirs:
        trash_dir = _get_trash_dir(pkg_dir)
        try:
            log.debug("Trying to delete the trash dir %s" % trash_dir)
            rm_rf(trash_dir, max_retries=1, trash=False)
        except OSError as e:
            log.debug("Could not delete the trash dir %s (%s)" % (trash_dir, e))


def move_to_trash(prefix, f, tempdir=None):
    """
    Move a file or folder f from prefix to the trash

    tempdir is a deprecated parameter, and will be ignored.

    This function is deprecated in favor of `move_path_to_trash`.
    """
    return move_path_to_trash(join(prefix, f) if f else prefix)


def move_path_to_trash(path):
    """
    Move a path to the trash
    """
    # Try deleting the trash every time we use it.
    delete_trash()
    from conda.config import root_dir

    for pkg_dir in pkgs_dirs:
        import tempfile
        trash_dir = _get_trash_dir(pkg_dir)

        try:
            os.makedirs(trash_dir)
        except OSError as e1:
            if e1.errno != errno.EEXIST:
                continue

        trash_dir = tempfile.mkdtemp(dir=trash_dir)
        trash_dir = join(trash_dir, _safe_relpath(os.path.dirname(path), root_dir))

        try:
            os.makedirs(trash_dir)
        except OSError as e2:
            if e2.errno != errno.EEXIST:
                continue

        try:
            shutil.move(path, trash_dir)
        except OSError as e:
            log.debug("Could not move %s to %s (%s)" % (path, trash_dir, e))
        else:
            delete_linked_data_any(path)
            return True

    log.debug("Could not move %s to trash" % path)
    return False


def link(prefix, dist, linktype=LINK_HARD, index=None, shortcuts=False):
    """
    Set up a package in a specified (environment) prefix.  We assume that
    the package has been extracted (using extract() above).
    """
    index = index or {}
    source_dir = is_extracted(dist)
    assert source_dir is not None
    pkgs_dir = dirname(source_dir)
    log.debug('pkgs_dir=%r, prefix=%r, dist=%r, linktype=%r' %
              (pkgs_dir, prefix, dist, linktype))

    if not run_script(source_dir, dist, 'pre-link', prefix):
        sys.exit('Error: pre-link failed: %s' % dist)

    info_dir = join(source_dir, 'info')
    files = list(yield_lines(join(info_dir, 'files')))
    has_prefix_files = read_has_prefix(join(info_dir, 'has_prefix'))
    no_link = read_no_link(info_dir)

    with Locked(prefix, dist), Locked(pkgs_dir, dist):
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
                    if on_win:
                        try:
                            move_path_to_trash(dst)
                        except ImportError:
                            # This shouldn't be an issue in the installer anyway
                            pass

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

        # make sure that the child environment behaves like the parent,
        #    wrt user/system install on win
        # This is critical for doing shortcuts correctly
        if on_win:
            nonadmin = join(sys.prefix, ".nonadmin")
            if isfile(nonadmin):
                open(join(prefix, ".nonadmin"), 'w').close()

        if shortcuts:
            mk_menus(prefix, files, remove=False)

        if not run_script(prefix, dist, 'post-link'):
            sys.exit("Error: post-link failed for: %s" % dist)

        meta_dict = index.get(dist + '.tar.bz2', {})
        meta_dict['url'] = read_url(dist)
        try:
            alt_files_path = join(prefix, 'conda-meta', dist2filename(dist, '.files'))
            meta_dict['files'] = list(yield_lines(alt_files_path))
            os.unlink(alt_files_path)
        except IOError:
            meta_dict['files'] = files
        meta_dict['link'] = {'source': source_dir,
                             'type': link_name_map.get(linktype)}
        if 'icon' in meta_dict:
            meta_dict['icondata'] = read_icondata(source_dir)

        create_meta(prefix, dist, info_dir, meta_dict)


def unlink(prefix, dist):
    """
    Remove a package from the specified environment, it is an error if the
    package does not exist in the prefix.
    """
    with Locked(prefix, dist):
        run_script(prefix, dist, 'pre-unlink')

        meta = load_meta(prefix, dist)
        # Always try to run this - it should not throw errors where menus do not exist
        mk_menus(prefix, meta['files'], remove=True)
        dst_dirs1 = set()

        for f in meta['files']:
            dst = join(prefix, f)
            dst_dirs1.add(dirname(dst))
            try:
                os.unlink(dst)
            except OSError:  # file might not exist
                log.debug("could not remove file: '%s'" % dst)
                if on_win and os.path.exists(join(prefix, f)):
                    try:
                        log.debug("moving to trash")
                        move_path_to_trash(dst)
                    except ImportError:
                        # This shouldn't be an issue in the installer anyway
                        #   but it can potentially happen with importing conda.config
                        log.debug("cannot import conda.config; probably not an issue")

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


def duplicates_to_remove(dist_metas, keep_dists):
    """
    Returns the (sorted) list of distributions to be removed, such that
    only one distribution (for each name) remains.  `keep_dists` is an
    iterable of distributions (which are not allowed to be removed).
    """
    from collections import defaultdict

    keep_dists = set(keep_dists)
    ldists = defaultdict(set)  # map names to set of distributions
    for dist in dist_metas:
        name = name_dist(dist)
        ldists[name].add(dist)

    res = set()
    for dists in ldists.values():
        # `dists` is the group of packages with the same name
        if len(dists) == 1:
            # if there is only one package, nothing has to be removed
            continue
        if dists & keep_dists:
            # if the group has packages which are have to be kept, we just
            # take the set of packages which are in group but not in the
            # ones which have to be kept
            res.update(dists - keep_dists)
        else:
            # otherwise, we take lowest (n-1) (sorted) packages
            res.update(sorted(dists)[:-1])
    return sorted(res)


# =========================== end API functions ==========================


def main():
    # This CLI is only invoked from the self-extracting shell installers
    from optparse import OptionParser

    p = OptionParser(description="conda link tool used by installer")

    p.add_option('--file',
                 action="store",
                 help="path of a file containing distributions to link, "
                      "by default all packages extracted in the cache are "
                      "linked")

    p.add_option('--prefix',
                 action="store",
                 default=sys.prefix,
                 help="prefix (defaults to %default)")

    p.add_option('-v', '--verbose',
                 action="store_true")

    opts, args = p.parse_args()
    if args:
        p.error('no arguments expected')

    logging.basicConfig()

    prefix = opts.prefix
    pkgs_dir = join(prefix, 'pkgs')
    pkgs_dirs[0] = [pkgs_dir]
    if opts.verbose:
        print("prefix: %r" % prefix)

    if opts.file:
        idists = list(yield_lines(join(prefix, opts.file)))
    else:
        idists = sorted(extracted())

    linktype = (LINK_HARD
                if idists and try_hard_link(pkgs_dir, prefix, idists[0]) else
                LINK_COPY)
    if opts.verbose:
        print("linktype: %s" % link_name_map[linktype])

    for dist in idists:
        if opts.verbose:
            print("linking: %s" % dist)
        link(prefix, dist, linktype)

    messages(prefix)

    for dist in duplicates_to_remove(linked(prefix), idists):
        meta_path = join(prefix, 'conda-meta', dist + '.json')
        print("WARNING: unlinking: %s" % meta_path)
        try:
            os.rename(meta_path, meta_path + '.bak')
        except OSError:
            rm_rf(meta_path)


if __name__ == '__main__':
    main()
