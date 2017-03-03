# this module contains miscellaneous stuff which enventually could be moved
# into other places

from __future__ import absolute_import, division, print_function, unicode_literals

from collections import defaultdict
import os
from os.path import (abspath, dirname, exists, expanduser, isdir, isfile, join,
                     relpath)
import re
import shutil
import sys

from ._vendor.auxlib.path import expand
from .base.context import context
from .common.compat import iteritems, iterkeys, itervalues, on_win, open
from .common.path import url_to_path, win_path_ok
from .common.url import is_url, join_url, path_to_url
from .core.index import get_index, _supplement_index_with_cache
from .core.linked_data import linked_data
from .core.package_cache import PackageCache, ProgressiveFetchExtract
from .exceptions import CondaFileNotFoundError, CondaRuntimeError, ParseError
from .gateways.disk.delete import rm_rf
from .gateways.disk.link import islink
from .instructions import LINK, UNLINK
from .models.dist import Dist
from .models.index_record import IndexRecord
from .plan import execute_actions
from .resolve import MatchSpec, Resolve


def conda_installed_files(prefix, exclude_self_build=False):
    """
    Return the set of files which have been installed (using conda) into
    a given prefix.
    """
    res = set()
    for dist, meta in iteritems(linked_data(prefix)):
        if exclude_self_build and 'file_hash' in meta:
            continue
        res.update(set(meta.get('files', ())))
    return res


url_pat = re.compile(r'(?:(?P<url_p>.+)(?:[/\\]))?'
                     r'(?P<fn>[^/\\#]+\.tar\.bz2)'
                     r'(:?#(?P<md5>[0-9a-f]{32}))?$')
def explicit(specs, prefix, verbose=False, force_extract=True, index_args=None, index=None):
    actions = defaultdict(list)
    actions['PREFIX'] = prefix

    fetch_recs = {}
    for spec in specs:
        if spec == '@EXPLICIT':
            continue

        if not is_url(spec):
            spec = path_to_url(expand(spec))

        # parse URL
        m = url_pat.match(spec)
        if m is None:
            raise ParseError('Could not parse explicit URL: %s' % spec)
        url_p, fn, md5sum = m.group('url_p'), m.group('fn'), m.group('md5')
        url = join_url(url_p, fn)
        # url_p is everything but the tarball_basename and the md5sum

        # If the path points to a file in the package cache, we need to use
        # the dist name that corresponds to that package. The MD5 may not
        # match, but we will let PFE below worry about that
        dist = None
        if url.startswith('file:/'):
            path = win_path_ok(url_to_path(url))
            if dirname(path) in context.pkgs_dirs:
                if not exists(path):
                    raise CondaFileNotFoundError(path)
                pc_entry = PackageCache.tarball_file_in_cache(path)
                dist = pc_entry.dist
                url = dist.to_url() or pc_entry.get_urls_txt_value()
                md5sum = md5sum or pc_entry.md5sum
        dist = dist or Dist(url)
        fetch_recs[dist] = {'md5': md5sum, 'url': url}

    # perform any necessary fetches and extractions
    if verbose:
        from .console import setup_verbose_handlers
        setup_verbose_handlers()
    link_dists = tuple(iterkeys(fetch_recs))
    pfe = ProgressiveFetchExtract(fetch_recs, link_dists)
    pfe.execute()

    # Now get the index---but the only index we need is the package cache
    index = {}
    _supplement_index_with_cache(index, ())

    # unlink any installed packages with same package name
    link_names = {index[d]['name'] for d in link_dists}
    actions[UNLINK].extend(d for d, r in iteritems(linked_data(prefix))
                           if r['name'] in link_names)

    # need to get the install order right, especially to install python in the prefix
    #  before python noarch packages
    r = Resolve(index)
    actions[LINK].extend(link_dists)
    actions[LINK] = r.dependency_sort({r.package_name(dist): dist for dist in actions[LINK]})

    execute_actions(actions, index, verbose=verbose)
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
    if on_win and exists(join(context.root_prefix, '.nonadmin')):
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

    # Discard conda, conda-env and any package that depends on them
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
            if name == "conda-env":
                filter["conda-env"] = dist
                found = True
                break
            for dep in info.get('depends', []):
                if MatchSpec(dep).name in filter:
                    filter[name] = dist
                    found = True

    if filter:
        if not quiet:
            fh = sys.stderr if context.json else sys.stdout
            print('The following packages cannot be cloned out of the root environment:', file=fh)
            for pkg in itervalues(filter):
                print(' - ' + pkg.dist_name, file=fh)
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
            name = dist.dist_name
            fn = dist.to_filename()
            fkeys = [d for d in r.index.keys() if r.index[d]['fn'] == fn]
            if fkeys:
                del drecs[dist]
                dist_str = sorted(fkeys, key=r.version_key, reverse=True)[0]
                drecs[Dist(dist_str)] = r.index[dist_str]
            else:
                notfound.append(fn)
    if notfound:
        what = "Package%s " % ('' if len(notfound) == 1 else 's')
        notfound = '\n'.join(' - ' + fn for fn in notfound)
        msg = '%s missing in current %s channels:%s' % (what, context.subdir, notfound)
        raise CondaRuntimeError(msg)

    # Assemble the URL and channel list
    urls = {}
    for dist, info in iteritems(drecs):
        fkey = dist
        if fkey not in index:
            index[fkey] = IndexRecord.from_objects(info, not_fetched=True)
            r = None
        urls[dist] = info['url']

    if r is None:
        r = Resolve(index)
    dists = r.dependency_sort({d.quad[0]: d for d in urls.keys()})
    urls = [urls[d] for d in dists]

    if verbose:
        print('Packages: %d' % len(dists))
        print('Files: %d' % len(untracked_files))

    for f in untracked_files:
        src = join(prefix1, f)
        dst = join(prefix2, f)
        dst_dir = dirname(dst)
        if islink(dst_dir) or isfile(dst_dir):
            rm_rf(dst_dir)
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
        return '%s/icons/%s' % (base_url, icon_fn)
    return ''


def list_prefixes():
    # Lists all the prefixes that conda knows about.
    for envs_dir in context.envs_dirs:
        if not isdir(envs_dir):
            continue
        for dn in sorted(os.listdir(envs_dir)):
            if dn.startswith('.'):
                continue
            prefix = join(envs_dir, dn)
            if isdir(prefix):
                prefix = join(envs_dir, dn)
                yield prefix

    yield context.root_prefix
