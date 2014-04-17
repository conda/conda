# this module contains miscellaneous stuff which enventually could be moved
# into other places

from __future__ import print_function, division, absolute_import

import os
import sys
import shutil
import subprocess
from collections import defaultdict
from distutils.spawn import find_executable
from os.path import (abspath, basename, dirname, expanduser, exists,
                     isdir, isfile, islink, join)

from conda import config
from conda import install
from conda.api import get_index
from conda.plan import (RM_EXTRACTED, EXTRACT, UNLINK, LINK,
                        ensure_linked_actions, execute_actions)
from conda.compat import iteritems



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


def rel_path(prefix, path):
    res = path[len(prefix) + 1:]
    if sys.platform == 'win32':
        res = res.replace('\\', '/')
    return res


def walk_prefix(prefix, ignore_predefined_files=True):
    """
    Return the set of all files in a given prefix directory.
    """
    res = set()
    prefix = abspath(prefix)
    ignore = {'pkgs', 'envs', 'conda-bld', 'conda-meta', '.conda_lock',
              'users', 'LICENSE.txt', 'info', 'conda-recipes',
              '.index', '.unionfs', '.nonadmin'}
    binignore = {'conda', 'activate', 'deactivate'}
    if sys.platform == 'darwin':
        ignore.update({'python.app', 'Launcher.app'})
    for fn in os.listdir(prefix):
        if ignore_predefined_files:
            if fn in ignore:
                continue
        if isfile(join(prefix, fn)):
            res.add(fn)
            continue
        for root, dirs, files in os.walk(join(prefix, fn)):
            for fn2 in files:
                if ignore_predefined_files:
                    if root == join(prefix, 'bin') and fn2 in binignore:
                        continue
                res.add(rel_path(prefix, join(root, fn2)))
            for dn in dirs:
                path = join(root, dn)
                if islink(path):
                    res.add(rel_path(prefix, path))
    return res


def untracked(prefix, exclude_self_build=False):
    """
    Return (the set) of all untracked files for a given prefix.
    """
    conda_files = conda_installed_files(prefix, exclude_self_build)
    return {path for path in walk_prefix(prefix) - conda_files
            if not (path.endswith('~') or
                     (sys.platform=='darwin' and path.endswith('.DS_Store')) or
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


def clone_env(prefix1, prefix2, verbose=True):
    """
    clone existing prefix1 into new prefix2
    """
    untracked_files = untracked(prefix1)
    dists = discard_conda(install.linked(prefix1))
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

        try:
            with open(src, 'rb') as fi:
                data = fi.read()
        except IOError:
            continue

        try:
            s = data.decode('utf-8')
            s = s.replace(prefix1, prefix2)
            data = s.encode('utf-8')
        except UnicodeDecodeError: # data is binary
            pass

        with open(dst, 'wb') as fo:
            fo.write(data)
        shutil.copystat(src, dst)

    actions = ensure_linked_actions(dists, prefix2)
    execute_actions(actions, index=get_index(), verbose=verbose)


def install_local_packages(prefix, paths, verbose=False):
    # copy packages to pkgs dir
    dists = []
    for src_path in paths:
        assert src_path.endswith('.tar.bz2')
        fn = basename(src_path)
        dists.append(fn[:-8])
        dst_path = join(config.pkgs_dirs[0], fn)
        if abspath(src_path) == abspath(dst_path):
            continue
        shutil.copyfile(src_path, dst_path)

    actions = defaultdict(list)
    actions['PREFIX'] = prefix
    actions['op_order'] = RM_EXTRACTED, EXTRACT, UNLINK, LINK
    for dist in dists:
        actions[RM_EXTRACTED].append(dist)
        actions[EXTRACT].append(dist)
        if install.is_linked(prefix, dist):
            actions[UNLINK].append(dist)
        actions[LINK].append(dist)
    execute_actions(actions, verbose=verbose)


def launch(fn, prefix=config.root_dir, additional_args=None):
    info = install.is_linked(prefix, fn[:-8])
    if info is None:
        return None

    if not info.get('type') == 'app':
        raise Exception('Not an application: %s' % fn)

    # prepend the bin directory to the path
    fmt = r'%s\Scripts;%s' if sys.platform == 'win32' else '%s/bin:%s'
    env = {'PATH': fmt % (abspath(prefix), os.getenv('PATH'))}
    # copy existing environment variables, but not anything with PATH in it
    for k, v in iteritems(os.environ):
        if 'PATH' not in k:
            env[k] = v
    # allow updating environment variables from metadata
    if 'app_env' in info:
        env.update(info['app_env'])

    # call the entry command
    args = info['app_entry'].split()
    args = [a.replace('${PREFIX}', prefix) for a in args]
    arg0 = find_executable(args[0], env['PATH'])
    if arg0 is None:
        raise Exception('Executable not found: %s' % args[0])
    args[0] = arg0

    cwd = abspath(expanduser('~'))
    if additional_args:
        args.extend(additional_args)
    return subprocess.Popen(args, cwd=cwd , env=env)


if __name__ == '__main__':
    from optparse import OptionParser

    p = OptionParser(usage="usage: %prog [options] DIST/FN [ADDITIONAL ARGS]")
    p.add_option('-p', '--prefix',
                 action="store",
                 default=sys.prefix,
                 help="prefix (defaults to %default)")
    opts, args = p.parse_args()

    if len(args) == 0:
        p.error('at least one argument expected')

    fn = args[0]
    if not fn.endswith('.tar.bz2'):
        fn += '.tar.bz2'
    p = launch(fn, opts.prefix, args[1:])
    print('PID:', p.pid)
