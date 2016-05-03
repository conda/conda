# this module contains miscellaneous stuff which enventually could be moved
# into other places

from __future__ import print_function, division, absolute_import

import os
import re
import shutil
import sys
from collections import defaultdict
from os.path import (abspath, dirname, expanduser, exists,
                     isdir, isfile, islink, join, relpath)

from conda import config
from conda import install
from conda import utils
from conda import fetch
from conda.api import get_index
from conda.compat import iteritems
from conda.instructions import RM_EXTRACTED, EXTRACT, UNLINK, LINK
from conda.plan import ensure_linked_actions, execute_actions
from conda.resolve import Resolve


def conda_installed_files(prefix, exclude_self_build=False):
    """
    Return the set of files which have been installed (using conda) into
    a given prefix.
    """
    res = set()
    for dist in install.linked(prefix):
        meta = install.is_linked(prefix, dist)
        if exclude_self_build and 'file_hash' in meta:
            continue
        res.update(set(meta['files']))
    return res


def force_extract_and_link(dists, prefix, verbose=False):
    actions = defaultdict(list)
    actions['PREFIX'] = prefix
    actions['op_order'] = RM_EXTRACTED, EXTRACT, UNLINK, LINK
    # maps names of installed packages to dists
    linked = {install.name_dist(dist): dist for dist in install.linked(prefix)}
    for dist in dists:
        actions[RM_EXTRACTED].append(dist)
        actions[EXTRACT].append(dist)
        # unlink any installed package with that name
        name = install.name_dist(dist)
        if name in linked:
            actions[UNLINK].append(linked[name])
        actions[LINK].append(dist)
    execute_actions(actions, verbose=verbose)


url_pat = re.compile(r'(?P<url>.+)/(?P<fn>[^/#]+\.tar\.bz2)'
                     r'(:?#(?P<md5>[0-9a-f]{32}))?$')
def explicit(urls, prefix, verbose=True):
    import conda.fetch as fetch
    from conda.utils import md5_file

    dists = []
    for url in urls:
        if url == '@EXPLICIT':
            continue
        print("Fetching: %s" % url)
        m = url_pat.match(url)
        fn, url_p = (m.group('fn'), m.group('url'))
        _, schannel = config.url_channel(url)
        if m is None:
            sys.exit("Error: Could not parse: %s" % url)
        fn = '%s::%s' % (schannel, fn)
        dists.append(fn[:-8])
        index = fetch.fetch_index((url_p + '/',))
        try:
            info = index[fn]
        except KeyError:
            sys.exit("Error: no package '%s' in index" % fn)
        if m.group('md5') and m.group('md5') != info['md5']:
            sys.exit("Error: MD5 in explicit files does not match index")
        found = False
        for dd in config.pkgs_dirs:
            pkg_path = join(dd, fn)
            if isfile(pkg_path):
                try:
                    if md5_file(pkg_path) == info['md5']:
                        found = True
                except KeyError:
                    sys.stderr.write('Warning: cannot lookup MD5 of: %s' % fn)
        if not found:
            fetch.fetch_pkg(info)

    force_extract_and_link(dists, prefix, verbose=verbose)


def rel_path(prefix, path, windows_forward_slashes=True):
    res = path[len(prefix) + 1:]
    if sys.platform == 'win32' and windows_forward_slashes:
        res = res.replace('\\', '/')
    return res


def walk_prefix(prefix, ignore_predefined_files=True, windows_forward_slashes=True):
    """
    Return the set of all files in a given prefix directory.
    """
    res = set()
    prefix = abspath(prefix)
    ignore = {'pkgs', 'envs', 'conda-bld', 'conda-meta', '.conda_lock',
              'users', 'LICENSE.txt', 'info', 'conda-recipes', '.index',
              '.unionfs', '.nonadmin'}
    binignore = {'conda', 'activate', 'deactivate'}
    if sys.platform == 'darwin':
        ignore.update({'python.app', 'Launcher.app'})
    for fn in os.listdir(prefix):
        if ignore_predefined_files and fn in ignore:
            continue
        if isfile(join(prefix, fn)):
            res.add(fn)
            continue
        for root, dirs, files in os.walk(join(prefix, fn)):
            should_ignore = ignore_predefined_files and root == join(prefix, 'bin')
            for fn2 in files:
                if should_ignore and fn2 in binignore:
                    continue
                res.add(relpath(join(root, fn2), prefix))
            for dn in dirs:
                path = join(root, dn)
                if islink(path):
                    res.add(relpath(path, prefix))

    if sys.platform == 'win32' and windows_forward_slashes:
        return {path.replace('\\', '/') for path in res}
    else:
        return res


def untracked(prefix, exclude_self_build=False):
    """
    Return (the set) of all untracked files for a given prefix.
    """
    conda_files = conda_installed_files(prefix, exclude_self_build)
    return {path for path in walk_prefix(prefix) - conda_files
            if not (path.endswith('~') or
                    (sys.platform == 'darwin' and path.endswith('.DS_Store')) or
                    (path.endswith('.pyc') and path[:-1] in conda_files))}


def which_prefix(path):
    """
    given the path (to a (presumably) conda installed file) return the
    environment prefix in which the file in located
    """
    prefix = abspath(path)
    while True:
        if isdir(join(prefix, 'conda-meta')):
            # we found the it, so let's return it
            return prefix
        if prefix == dirname(prefix):
            # we cannot chop off any more directories, so we didn't find it
            return None
        prefix = dirname(prefix)


def which_package(path):
    """
    given the path (of a (presumably) conda installed file) iterate over
    the conda packages the file came from.  Usually the iteration yields
    only one package.
    """
    path = abspath(path)
    prefix = which_prefix(path)
    if prefix is None:
        raise RuntimeError("could not determine conda prefix from: %s" % path)
    for dist in install.linked(prefix):
        meta = install.is_linked(prefix, dist)
        if any(abspath(join(prefix, f)) == path for f in meta['files']):
            yield dist


def discard_conda(dists):
    return [dist for dist in dists if not install.name_dist(dist) == 'conda']


def touch_nonadmin(prefix):
    """
    Creates $PREFIX/.nonadmin if sys.prefix/.nonadmin exists (on Windows)
    """
    if sys.platform == 'win32' and exists(join(config.root_dir, '.nonadmin')):
        if not isdir(prefix):
            os.makedirs(prefix)
        with open(join(prefix, '.nonadmin'), 'w') as fo:
            fo.write('')


def append_env(prefix):
    dir_path = abspath(expanduser('~/.conda'))
    try:
        if not isdir(dir_path):
            os.mkdir(dir_path)
        with open(join(dir_path, 'environments.txt'), 'a') as f:
            f.write('%s\n' % prefix)
    except IOError:
        pass


def clone_env(prefix1, prefix2, verbose=True, quiet=False, index=None):
    """
    clone existing prefix1 into new prefix2
    """
    untracked_files = untracked(prefix1)
    dists = discard_conda(install.linked(prefix1))

    if verbose:
        print('Packages: %d' % len(dists))
        print('Files: %d' % len(untracked_files))

    for f in untracked_files:
        src = join(prefix1, f)
        dst = join(prefix2, f)
        dst_dir = dirname(dst)
        if islink(dst_dir) or isfile(dst_dir):
            os.unlink(dst_dir)
        if not isdir(dst_dir):
            os.makedirs(dst_dir)
        if islink(src):
            os.symlink(os.readlink(src), dst)
            continue

        try:
            with open(src, 'rb') as fi:
                data = fi.read()
        except IOError:
            continue

        try:
            s = data.decode('utf-8')
            s = s.replace(prefix1, prefix2)
            data = s.encode('utf-8')
        except UnicodeDecodeError:  # data is binary
            pass

        with open(dst, 'wb') as fo:
            fo.write(data)
        shutil.copystat(src, dst)

    if index is None:
        index = get_index()

    r = Resolve(index)
    sorted_dists = r.dependency_sort(dists)

    actions = ensure_linked_actions(sorted_dists, prefix2)
    execute_actions(actions, index=index, verbose=not quiet)

    return actions, untracked_files


def install_local_packages(prefix, paths, verbose=False):
    # copy packages to pkgs dir
    dists = []
    for url in paths:
        assert url.endswith('.tar.bz2')
        if not config.is_url(url):
            url = utils.url_path(url)
        url_path, fn = url.rsplit('/', 1)
        schannel = None
        if url_path.startswith('file://'):
            for dd in config.pkgs_dirs:
                if url_path == utils.url_path(dd):
                    schannel = install.load_meta(dd, dist)
        if not schannel:
            _, schannel = config.url_channel(url)
            info = {'fn': fn, 'url': url, 'schannel': schannel, 'md5': None}
            fetch.fetch_pkg(info)
        dists.append('%s::%s' % (schannel, fn[:-8]))
    force_extract_and_link(dists, prefix, verbose=verbose)


def environment_for_conda_environment(prefix=config.root_dir):
    # prepend the bin directory to the path
    fmt = r'%s\Scripts' if sys.platform == 'win32' else '%s/bin'
    binpath = fmt % abspath(prefix)
    path = os.path.pathsep.join([binpath, os.getenv('PATH')])
    env = {'PATH': path}
    # copy existing environment variables, but not anything with PATH in it
    for k, v in iteritems(os.environ):
        if k != 'PATH':
            env[k] = v
    return binpath, env


def make_icon_url(info):
    if 'channel' in info and 'icon' in info:
        base_url = dirname(info['channel'].rstrip('/'))
        icon_fn = info['icon']
        # icon_cache_path = join(config.pkgs_dir, 'cache', icon_fn)
        # if isfile(icon_cache_path):
        #    return url_path(icon_cache_path)
        return '%s/icons/%s' % (base_url, icon_fn)
    return ''


def list_prefixes():
    # Lists all the prefixes that conda knows about.
    for envs_dir in config.envs_dirs:
        if not isdir(envs_dir):
            continue
        for dn in sorted(os.listdir(envs_dir)):
            if dn.startswith('.'):
                continue
            prefix = join(envs_dir, dn)
            if isdir(prefix):
                prefix = join(envs_dir, dn)
                yield prefix

    yield config.root_dir
