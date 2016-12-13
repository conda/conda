# this module contains miscellaneous stuff which enventually could be moved
# into other places

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import re
import shutil
import sys
from collections import defaultdict
from os.path import (abspath, dirname, exists, expanduser, isdir, isfile, islink, join,
                     relpath)

from ._vendor.auxlib.path import expand
from .base.context import context
from .common.compat import iteritems, iterkeys, itervalues, odict, on_win
from .common.path import url_to_path
from .common.url import is_url, join_url, path_to_url
from .core.index import get_index
from .core.linked_data import is_linked, linked as install_linked, linked_data
from .exceptions import (CondaRuntimeError, ParseError)
from .gateways.disk.delete import rm_rf
from .gateways.disk.read import compute_md5sum
from .instructions import EXTRACT, FETCH, LINK, RM_EXTRACTED, RM_FETCHED, SYMLINK_CONDA, UNLINK
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
    for dist in install_linked(prefix):
        meta = is_linked(prefix, dist)
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
    actions['op_order'] = RM_FETCHED, FETCH, RM_EXTRACTED, EXTRACT, UNLINK, LINK, SYMLINK_CONDA
    linked = {dist.name: dist for dist in install_linked(prefix)}
    index_args = index_args or {}
    index = index or {}

    # get our index
    index_args = index_args or {}
    index.update(get_index(
        channel_urls=context.channels,
        prepend=False,
        platform=context.subdir,
        use_local=index_args.get('use_local', False),
        use_cache=index_args.get('use_cache', context.offline),
        unknown=index_args.get('unknown', False),
        prefix=index_args.get('prefix', False),
    ))

    def spec_to_parsed_url(spec):
        if spec == '@EXPLICIT':
            return None, None

        if not is_url(spec):
            spec = path_to_url(expand(spec))

        # parse URL
        m = url_pat.match(spec)
        if m is None:
            raise ParseError('Could not parse explicit URL: %s' % spec)
        url_p, fn, md5sum = m.group('url_p'), m.group('fn'), m.group('md5')
        # url_p is everything but the tarball_basename and the md5sum

        url = join_url(url_p, fn)
        return url, md5sum

    def url_details_to_dist_record(url, md5sum):
        dist = Dist(url)
        if dist in index:
            record = index[dist]
            # TODO: we should be able to query across channels for no-channel dist + md5sum matches
        elif url.startswith('file:/'):
            md5sum = md5sum or compute_md5sum(url_to_path(url))
            record = IndexRecord(**{
                'fn': dist.to_filename(),
                'url': url,
                'md5': md5sum,
                'build': dist.build_string,
                'build_number': dist.build_number,
                'name': dist.name,
                'version': dist.version,
            })
        else:
            # non-local url that's not in index
            record = IndexRecord(**{
                'fn': dist.to_filename(),
                'url': url,
                'md5': md5sum,
                'build': dist.build_string,
                'build_number': dist.build_number,
                'name': dist.name,
                'version': dist.version,
            })
        return dist, record

    parsed_urls = (spec_to_parsed_url(spec) for spec in specs)
    link_index = odict(url_details_to_dist_record(url, md5sum)
                       for url, md5sum in parsed_urls if url)
    link_dists = tuple(iterkeys(link_index))

    # merge new link_index into index
    for dist, record in iteritems(link_index):
        _fetched_record = index.get(dist)
        index[dist] = (IndexRecord.from_objects(record, _fetched_record)
                       if _fetched_record else record)

    # unlink any installed packages with same package name
    unlink_dists = tuple(linked[dist.name] for dist in link_dists if dist.name in linked)

    for unlink_dist in unlink_dists:
        actions[UNLINK].append(unlink_dist)

    for link_dist in link_dists:
        actions[LINK].append(link_dist)

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
    if on_win and exists(join(context.root_dir, '.nonadmin')):
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
            print('The following packages cannot be cloned out of the root environment:')
            for pkg in itervalues(filter):
                print(' - ' + pkg.dist_name)
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
        # icon_cache_path = join(pkgs_dir, 'cache', icon_fn)
        # if isfile(icon_cache_path):
        #    return url_path(icon_cache_path)
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

    yield context.root_dir
