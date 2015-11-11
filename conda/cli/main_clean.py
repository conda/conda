# (c) 2012# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
from __future__ import print_function, division, absolute_import

import os
import sys
from collections import defaultdict

from os.path import join, getsize, isdir
from os import lstat, walk, listdir

from conda.cli import common
import conda.config as config
from conda.utils import human_bytes
from conda.install import rm_rf

descr = """
Remove unused packages and caches.
"""

example = """
Examples:

    conda clean --tarballs
"""

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'clean',
        description=descr,
        help=descr,
        epilog=example,
    )
    common.add_parser_yes(p)
    common.add_parser_json(p)
    p.add_argument(
        "-i", "--index-cache",
        action="store_true",
        help="Remove index cache.",
    )
    p.add_argument(
        "-l", "--lock",
        action="store_true",
        help="Remove all conda lock files.",
    )
    p.add_argument(
        "-t", "--tarballs",
        action="store_true",
        help="Remove cached package tarballs.",
    )
    p.add_argument(
        '-p', '--packages',
        action='store_true',
        help="""Remove unused cached packages. Warning: this does not check
    for symlinked packages.""",
    )
    p.add_argument(
        '-s', '--source-cache',
        action='store_true',
        help="""Remove files from the source cache of conda build.""",
    )
    p.set_defaults(func=execute)


def find_lock():
    from os.path import join

    from conda.lock import LOCKFN

    lock_dirs = config.pkgs_dirs[:]
    lock_dirs += [config.root_dir]
    for envs_dir in config.envs_dirs:
        if os.path.exists(envs_dir):
            for fn in os.listdir(envs_dir):
                if os.path.isdir(join(envs_dir, fn)):
                    lock_dirs.append(join(envs_dir, fn))

    try:
        from conda_build.config import croot
        lock_dirs.append(croot)
    except ImportError:
        pass

    for dir in lock_dirs:
        if not os.path.exists(dir):
            continue
        for dn in os.listdir(dir):
            if os.path.isdir(join(dir, dn)) and dn.startswith(LOCKFN):
                path = join(dir, dn)
                yield path


def rm_lock(locks, verbose=True):
    for path in locks:
        if verbose:
            print('removing: %s' % path)
        os.rmdir(path)


def find_tarballs():
    pkgs_dirs = defaultdict(list)
    for pkgs_dir in config.pkgs_dirs:
        if not isdir(pkgs_dir):
            continue
        for fn in os.listdir(pkgs_dir):
            if fn.endswith('.tar.bz2') or fn.endswith('.tar.bz2.part'):
                pkgs_dirs[pkgs_dir].append(fn)

    totalsize = 0
    for pkgs_dir in pkgs_dirs:
        for fn in pkgs_dirs[pkgs_dir]:
            size = getsize(join(pkgs_dir, fn))
            totalsize += size

    return pkgs_dirs, totalsize


def rm_tarballs(args, pkgs_dirs, totalsize, verbose=True):
    if verbose:
        for pkgs_dir in pkgs_dirs:
            print('Cache location: %s' % pkgs_dir)

    if not any(pkgs_dirs[i] for i in pkgs_dirs):
        if verbose:
            print("There are no tarballs to remove")
        return

    if verbose:
        print("Will remove the following tarballs:")
        print()

        for pkgs_dir in pkgs_dirs:
            print(pkgs_dir)
            print('-'*len(pkgs_dir))
            fmt = "%-40s %10s"
            for fn in pkgs_dirs[pkgs_dir]:
                size = getsize(join(pkgs_dir, fn))
                print(fmt % (fn, human_bytes(size)))
            print()
        print('-' * 51) # From 40 + 1 + 10 in fmt
        print(fmt % ('Total:', human_bytes(totalsize)))
        print()

    if not args.json:
        common.confirm_yn(args)
    if args.json and args.dry_run:
        return

    for pkgs_dir in pkgs_dirs:
        for fn in pkgs_dirs[pkgs_dir]:
            if os.access(os.path.join(pkgs_dir, fn), os.W_OK):
                if verbose:
                    print("Removing %s" % fn)
                os.unlink(os.path.join(pkgs_dir, fn))
            else:
                if verbose:
                    print("WARNING: cannot remove, file permissions: %s" % fn)


def find_pkgs():
    # TODO: This doesn't handle packages that have hard links to files within
    # themselves, like bin/python3.3 and bin/python3.3m in the Python package
    warnings = []

    pkgs_dirs = defaultdict(list)
    for pkgs_dir in config.pkgs_dirs:
        if not os.path.exists(pkgs_dir):
            print("WARNING: {0} does not exist".format(pkgs_dir))
            continue
        pkgs = [i for i in listdir(pkgs_dir) if isdir(join(pkgs_dir, i)) and
            # Only include actual packages
            isdir(join(pkgs_dir, i, 'info'))]
        for pkg in pkgs:
            breakit = False
            for root, dir, files in walk(join(pkgs_dir, pkg)):
                if breakit:
                    break
                for fn in files:
                    try:
                        stat = lstat(join(root, fn))
                    except OSError as e:
                        warnings.append((fn, e))
                        continue
                    if stat.st_nlink > 1:
                        # print('%s is installed: %s' % (pkg, join(root, fn)))
                        breakit = True
                        break
            else:
                pkgs_dirs[pkgs_dir].append(pkg)

    totalsize = 0
    pkgsizes = defaultdict(list)
    for pkgs_dir in pkgs_dirs:
        for pkg in pkgs_dirs[pkgs_dir]:
            pkgsize = 0
            for root, dir, files in walk(join(pkgs_dir, pkg)):
                for fn in files:
                    # We don't have to worry about counting things twice:  by
                    # definition these files all have a link count of 1!
                    size = lstat(join(root, fn)).st_size
                    totalsize += size
                    pkgsize += size
            pkgsizes[pkgs_dir].append(pkgsize)

    return pkgs_dirs, warnings, totalsize, pkgsizes


def rm_pkgs(args, pkgs_dirs, warnings, totalsize, pkgsizes,
            verbose=True):
    if verbose:
        for pkgs_dir in pkgs_dirs:
            print('Cache location: %s' % pkgs_dir)
            for fn, exception in warnings:
                print(exception)

    if not any(pkgs_dirs[i] for i in pkgs_dirs):
        if verbose:
            print("There are no unused packages to remove")
        return

    if verbose:
        print("Will remove the following packages:")
        for pkgs_dir in pkgs_dirs:
            print(pkgs_dir)
            print('-' * len(pkgs_dir))
            print()
            fmt = "%-40s %10s"
            for pkg, pkgsize in zip(pkgs_dirs[pkgs_dir], pkgsizes[pkgs_dir]):
                print(fmt % (pkg, human_bytes(pkgsize)))
            print()
        print('-' * 51) # 40 + 1 + 10 in fmt
        print(fmt % ('Total:', human_bytes(totalsize)))
        print()

    if not args.json:
        common.confirm_yn(args)
    if args.json and args.dry_run:
        return

    for pkgs_dir in pkgs_dirs:
        for pkg in pkgs_dirs[pkgs_dir]:
            if verbose:
                print("removing %s" % pkg)
            rm_rf(join(pkgs_dir, pkg))


def rm_index_cache():
    from conda.install import rm_rf

    rm_rf(join(config.pkgs_dirs[0], 'cache'))

def find_source_cache():
    try:
        import conda_build.source
    except ImportError:
        return {
            'warnings': ["conda-build is not installed; could not clean source cache"],
            'cache_dirs': [],
            'cache_sizes': {},
            'total_size': 0,
        }

    cache_dirs = {
        'source cache': conda_build.source.SRC_CACHE,
        'git cache': conda_build.source.GIT_CACHE,
        'hg cache': conda_build.source.HG_CACHE,
        'svn cache': conda_build.source.SVN_CACHE,
    }

    sizes = {}
    totalsize = 0
    for cache_type, cache_dir in cache_dirs.items():
        dirsize = 0
        for root, d, files in walk(cache_dir):
            for fn in files:
                size = lstat(join(root, fn)).st_size
                totalsize += size
                dirsize += size
        sizes[cache_type] = dirsize

    return {
        'warnings': [],
        'cache_dirs': cache_dirs,
        'cache_sizes': sizes,
        'total_size': totalsize,
        }


def rm_source_cache(args, cache_dirs, warnings, cache_sizes, total_size):
    verbose = not args.json
    if warnings:
        if verbose:
            for warning in warnings:
                print(warning, file=sys.stderr)
        return

    for cache_type in cache_dirs:
        print("%s (%s)" % (cache_type, cache_dirs[cache_type]))
        print("%-40s %10s" % ("Size:",
            human_bytes(cache_sizes[cache_type])))
        print()

    print("%-40s %10s" % ("Total:", human_bytes(total_size)))

    if not args.json:
        common.confirm_yn(args)
    if args.json and args.dry_run:
        return

    for dir in cache_dirs.values():
        print("Removing %s" % dir)
        rm_rf(dir)

def execute(args, parser):
    json_result = {
        'success': True
    }

    if args.lock:
        locks = list(find_lock())
        json_result['lock'] = {
            'files': locks
        }
        rm_lock(locks, verbose=not args.json)

    if args.tarballs:
        pkgs_dirs, totalsize = find_tarballs()
        first = sorted(pkgs_dirs)[0] if pkgs_dirs else ''
        json_result['tarballs'] = {
            'pkgs_dir': first, # Backwards compabitility
            'pkgs_dirs': dict(pkgs_dirs),
            'files': pkgs_dirs[first], # Backwards compatibility
            'total_size': totalsize
        }
        rm_tarballs(args, pkgs_dirs, totalsize, verbose=not args.json)

    if args.index_cache:
        json_result['index_cache'] = {
            'files': [join(config.pkgs_dirs[0], 'cache')]
        }
        rm_index_cache()

    if args.packages:
        pkgs_dirs, warnings, totalsize, pkgsizes = find_pkgs()
        first = sorted(pkgs_dirs)[0] if pkgs_dirs else ''
        json_result['packages'] = {
            'pkgs_dir': first, # Backwards compatibility
            'pkgs_dirs': dict(pkgs_dirs),
            'files': pkgs_dirs[first], # Backwards compatibility
            'total_size': totalsize,
            'warnings': warnings,
            'pkg_sizes': {i: dict(zip(pkgs_dirs[i], pkgsizes[i])) for i in pkgs_dirs},
        }
        rm_pkgs(args, pkgs_dirs,  warnings, totalsize, pkgsizes,
                verbose=not args.json)

    if args.source_cache:
        json_result['source_cache'] = find_source_cache()
        rm_source_cache(args, **json_result['source_cache'])

    if not (args.lock or args.tarballs or args.index_cache or args.packages or
        args.source_cache):
        common.error_and_exit(
            "One of {--lock, --tarballs, --index-cache, --packages, --source-cache} required",
            error_type="ValueError")

    if args.json:
        common.stdout_json(json_result)
