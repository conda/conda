# this module contains miscellaneous stuff which enventually could be moved
# into other places

from __future__ import print_function, division, absolute_import

import os
import re
import sys
import shlex
import shutil
import subprocess
from collections import defaultdict
from distutils.spawn import find_executable
from os.path import (abspath, basename, dirname, expanduser, exists,
                     isdir, isfile, islink, join)

from conda import config
from conda import install
from conda.api import get_index
from conda.instructions import RM_EXTRACTED, EXTRACT, UNLINK, LINK
from conda.plan import ensure_linked_actions, execute_actions
from conda.compat import iteritems
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
        if m is None:
            sys.exit("Error: Could not parse: %s" % url)
        fn = m.group('fn')
        dists.append(fn[:-8])
        index = fetch.fetch_index((m.group('url') + '/',))
        try:
            info = index[fn]
        except KeyError:
            sys.exit("Error: no package '%s' in index" % fn)
        if m.group('md5') and m.group('md5') != info['md5']:
            sys.exit("Error: MD5 in explicit files does not match index")
        pkg_path = join(config.pkgs_dirs[0], fn)
        if isfile(pkg_path):
            try:
                if md5_file(pkg_path) != info['md5']:
                    install.rm_rf(pkg_path)
                    fetch.fetch_pkg(info)
            except KeyError:
                sys.stderr.write('Warning: cannot lookup MD5 of: %s' % fn)
        else:
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
                res.add(rel_path(prefix, join(root, fn2), windows_forward_slashes=windows_forward_slashes))
            for dn in dirs:
                path = join(root, dn)
                if islink(path):
                    res.add(rel_path(prefix, path, windows_forward_slashes=windows_forward_slashes))
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
    pkgs_dir = config.pkgs_dirs[0]
    dists = []
    for src_path in paths:
        assert src_path.endswith('.tar.bz2')
        fn = basename(src_path)
        dists.append(fn[:-8])
        dst_path = join(pkgs_dir, fn)
        if abspath(src_path) == abspath(dst_path):
            continue
        shutil.copyfile(src_path, dst_path)

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


def launch(fn, prefix=config.root_dir, additional_args=None, background=False):
    info = install.is_linked(prefix, fn[:-8])
    if info is None:
        return None

    if not info.get('type') == 'app':
        raise TypeError('Not an application: %s' % fn)

    binpath, env = environment_for_conda_environment(prefix)
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
    if sys.platform == 'win32' and background:
        return subprocess.Popen(args, cwd=cwd, env=env, close_fds=False,
                                creationflags=subprocess.CREATE_NEW_CONSOLE)
    else:
        return subprocess.Popen(args, cwd=cwd, env=env, close_fds=False)


def execute_in_environment(cmd, prefix=config.root_dir, additional_args=None,
                           inherit=True):
    """Runs ``cmd`` in the specified environment.

    ``inherit`` specifies whether the child inherits stdio handles (for JSON
    output, we don't want to trample this process's stdout).
    """
    binpath, env = environment_for_conda_environment(prefix)

    if sys.platform == 'win32' and cmd == 'python':
        # python is located one directory up on Windows
        cmd = join(binpath, '..', cmd)

    args = shlex.split(cmd)
    if additional_args:
        args.extend(additional_args)

    if inherit:
        stdin, stdout, stderr = None, None, None
    else:
        stdin, stdout, stderr = subprocess.PIPE, subprocess.PIPE, subprocess.PIPE

    if sys.platform == 'win32' and not inherit:
        return subprocess.Popen(args, env=env, close_fds=False,
                                stdin=stdin, stdout=stdout, stderr=stderr,
                                creationflags=subprocess.CREATE_NEW_CONSOLE)
    else:
        return subprocess.Popen(args, env=env, close_fds=False,
                                stdin=stdin, stdout=stdout, stderr=stderr)


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
