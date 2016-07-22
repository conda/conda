# this module contains miscellaneous stuff which enventually could be moved
# into other places

from __future__ import print_function, division, absolute_import

import os
import re
import shutil
import sys
from collections import defaultdict
from os.path import (abspath, dirname, expanduser, exists,
                     isdir, isfile, islink, join, relpath, curdir)

from .api import get_index
from .compat import iteritems, itervalues
from .config import is_url, url_channel, root_dir, envs_dirs, subdir
from .exceptions import (CondaFileNotFoundError, ParseError, MD5MismatchError,
                         PackageNotFoundError, CondaRuntimeError)
from .install import (name_dist, linked as install_linked, is_fetched, is_extracted, is_linked,
                      linked_data, find_new_location, cached_url, dist2filename)
from .instructions import RM_FETCHED, FETCH, RM_EXTRACTED, EXTRACT, UNLINK, LINK, SYMLINK_CONDA
from .plan import execute_actions
from .resolve import Resolve, MatchSpec
from .utils import md5_file, path_to_url, on_win


def conda_installed_files(prefix, exclude_self_build=False):
    """
    Return the set of files which have been installed (using conda) into
    a given prefix.
    """
    res = set()
    for dist in install_linked(prefix):
        meta = is_linked(prefix, dist)
        if exclude_self_build and 'file_hash' in meta:
            continue
        res.update(set(meta['files']))
    return res

url_pat = re.compile(r'(?:(?P<url_p>.+)(?:[/\\]))?'
                     r'(?P<fn>[^/\\#]+\.tar\.bz2)'
                     r'(:?#(?P<md5>[0-9a-f]{32}))?$')
def explicit(specs, prefix, verbose=False, force_extract=True, index_args=None, index=None):
    actions = defaultdict(list)
    actions['PREFIX'] = prefix
    actions['op_order'] = RM_FETCHED, FETCH, RM_EXTRACTED, EXTRACT, UNLINK, LINK, SYMLINK_CONDA
    linked = {name_dist(dist): dist for dist in install_linked(prefix)}
    index_args = index_args or {}
    index = index or {}
    verifies = []
    channels = set()
    for spec in specs:
        if spec == '@EXPLICIT':
            continue

        # Format: (url|path)(:#md5)?
        m = url_pat.match(spec)
        if m is None:
            raise ParseError('Could not parse explicit URL: %s' % spec)
        url_p, fn, md5 = m.group('url_p'), m.group('fn'), m.group('md5')
        if not is_url(url_p):
            if url_p is None:
                url_p = curdir
            elif not isdir(url_p):
                raise CondaFileNotFoundError('file not found: %s' %
                                             join(url_p, fn))
            url_p = path_to_url(url_p).rstrip('/')
        url = "{0}/{1}".format(url_p, fn)

        # is_local: if the tarball is stored locally (file://)
        # is_cache: if the tarball is sitting in our cache
        is_local = url.startswith('file://')
        prefix = cached_url(url) if is_local else None
        is_cache = prefix is not None
        if is_cache:
            # Channel information from the cache
            schannel = 'defaults' if prefix == '' else prefix[:-2]
        else:
            # Channel information from the URL
            channel, schannel = url_channel(url)
            prefix = '' if schannel == 'defaults' else schannel + '::'

        fn = prefix + fn
        dist = fn[:-8]
        # Add explicit file to index so we'll be sure to see it later
        if is_local:
            index[fn] = {'fn': dist2filename(fn), 'url': url, 'md5': md5}
            verifies.append((fn, md5))

        pkg_path = is_fetched(dist)
        dir_path = is_extracted(dist)

        # Don't re-fetch unless there is an MD5 mismatch
        # Also remove explicit tarballs from cache, unless the path *is* to the cache
        if pkg_path and not is_cache and (is_local or md5 and md5_file(pkg_path) != md5):
            # This removes any extracted copies as well
            actions[RM_FETCHED].append(dist)
            pkg_path = dir_path = None

        # Don't re-extract unless forced, or if we can't check the md5
        if dir_path and (force_extract or md5 and not pkg_path):
            actions[RM_EXTRACTED].append(dist)
            dir_path = None

        if not dir_path:
            if not pkg_path:
                _, conflict = find_new_location(dist)
                if conflict:
                    actions[RM_FETCHED].append(conflict)
                if not is_local:
                    if fn not in index or index[fn].get('not_fetched'):
                        channels.add(schannel)
                    verifies.append((dist + '.tar.bz2', md5))
                actions[FETCH].append(dist)
            actions[EXTRACT].append(dist)

        # unlink any installed package with that name
        name = name_dist(dist)
        if name in linked:
            actions[UNLINK].append(linked[name])
        actions[LINK].append(dist)

    # Pull the repodata for channels we are using
    if channels:
        index_args = index_args or {}
        index_args = index_args.copy()
        index_args['prepend'] = False
        index_args['channel_urls'] = list(channels)
        index.update(get_index(**index_args))

    # Finish the MD5 verification
    for fn, md5 in verifies:
        info = index.get(fn)
        if info is None:
            raise PackageNotFoundError("no package '%s' in index" % fn)
        if md5 and 'md5' not in info:
            sys.stderr.write('Warning: cannot lookup MD5 of: %s' % fn)
        if md5 and info['md5'] != md5:
            raise MD5MismatchError('MD5 mismatch for: %s\n   spec: %s\n   repo: %s'
                                   % (fn, md5, info['md5']))

    execute_actions(actions, index=index, verbose=verbose)
    return actions


def rel_path(prefix, path, windows_forward_slashes=True):
    res = path[len(prefix) + 1:]
    if on_win and windows_forward_slashes:
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

    if on_win and windows_forward_slashes:
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


def touch_nonadmin(prefix):
    """
    Creates $PREFIX/.nonadmin if sys.prefix/.nonadmin exists (on Windows)
    """
    if on_win and exists(join(root_dir, '.nonadmin')):
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


def clone_env(prefix1, prefix2, verbose=True, quiet=False, index_args=None):
    """
    clone existing prefix1 into new prefix2
    """
    untracked_files = untracked(prefix1)

    # Discard conda and any package that depends on it
    drecs = linked_data(prefix1)
    filter = {}
    found = True
    while found:
        found = False
        for dist, info in iteritems(drecs):
            name = info['name']
            if name in filter:
                continue
            if name == 'conda':
                filter['conda'] = dist
                found = True
                break
            for dep in info.get('depends', []):
                if MatchSpec(dep).name in filter:
                    filter[name] = dist
                    found = True
    if filter:
        if not quiet:
            print('The following packages cannot be cloned out of the root environment:')
            for pkg in itervalues(filter):
                print(' - ' + pkg)
            drecs = {dist: info for dist, info in iteritems(drecs) if info['name'] not in filter}

    # Resolve URLs for packages that do not have URLs
    r = None
    index = {}
    unknowns = [dist for dist, info in iteritems(drecs) if not info.get('url')]
    notfound = []
    if unknowns:
        index_args = index_args or {}
        index = get_index(**index_args)
        r = Resolve(index, sort=True)
        for dist in unknowns:
            name = name_dist(dist)
            fn = dist2filename(dist)
            fkeys = [d for d in r.index.keys() if r.index[d]['fn'] == fn]
            if fkeys:
                del drecs[dist]
                dist = sorted(fkeys, key=r.version_key, reverse=True)[0]
                drecs[dist] = r.index[dist]
            else:
                notfound.append(fn)
    if notfound:
        what = "Package%s " % ('' if len(notfound) == 1 else 's')
        notfound = '\n'.join(' - ' + fn for fn in notfound)
        msg = '%s missing in current %s channels:%s' % (what, subdir, notfound)
        raise CondaRuntimeError(msg)

    # Assemble the URL and channel list
    urls = {}
    for dist, info in iteritems(drecs):
        fkey = dist + '.tar.bz2'
        if fkey not in index:
            info['not_fetched'] = True
            index[fkey] = info
            r = None
        urls[dist] = info['url']

    if r is None:
        r = Resolve(index)
    dists = r.dependency_sort(urls.keys())
    urls = [urls[d] for d in dists]

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

    actions = explicit(urls, prefix2, verbose=not quiet, index=index,
                       force_extract=False, index_args=index_args)
    return actions, untracked_files


def make_icon_url(info):
    if info.get('channel') and info.get('icon'):
        base_url = dirname(info['channel'])
        icon_fn = info['icon']
        # icon_cache_path = join(pkgs_dir, 'cache', icon_fn)
        # if isfile(icon_cache_path):
        #    return url_path(icon_cache_path)
        return '%s/icons/%s' % (base_url, icon_fn)
    return ''


def list_prefixes():
    # Lists all the prefixes that conda knows about.
    for envs_dir in envs_dirs:
        if not isdir(envs_dir):
            continue
        for dn in sorted(os.listdir(envs_dir)):
            if dn.startswith('.'):
                continue
            prefix = join(envs_dir, dn)
            if isdir(prefix):
                prefix = join(envs_dir, dn)
                yield prefix

    yield root_dir
