# (c) 2012-2016 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import defaultdict
from logging import getLogger
import os
from os import listdir, lstat, walk
from os.path import getsize, isdir, join
import sys

from .common import add_parser_json, add_parser_yes, confirm_yn, stdout_json
from ..base.constants import CONDA_TARBALL_EXTENSION
from ..base.context import context
from ..exceptions import ArgumentError
from ..gateways.disk.delete import rm_rf
from ..gateways.disk.link import CrossPlatformStLink
from ..utils import human_bytes

log = getLogger(__name__)

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
    add_parser_yes(p)
    add_parser_json(p)
    p.add_argument(
        "-a", "--all",
        action="store_true",
        help="Remove index cache, lock files, tarballs, "
             "unused cache packages, and source cache.",
    )
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


def find_tarballs():
    from ..core.package_cache import PackageCache
    pkgs_dirs = defaultdict(list)
    totalsize = 0
    part_ext = CONDA_TARBALL_EXTENSION + '.part'
    for package_cache in PackageCache.all_writable(context.pkgs_dirs):
        pkgs_dir = package_cache.pkgs_dir
        if not isdir(pkgs_dir):
            continue
        root, _, filenames = next(os.walk(pkgs_dir))
        for fn in filenames:
            if fn.endswith(CONDA_TARBALL_EXTENSION) or fn.endswith(part_ext):
                pkgs_dirs[pkgs_dir].append(fn)
                totalsize += getsize(join(root, fn))

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
        print('-' * 51)  # From 40 + 1 + 10 in fmt
        print(fmt % ('Total:', human_bytes(totalsize)))
        print()

    if not context.json:
        confirm_yn(args)
    if context.json and args.dry_run:
        return

    for pkgs_dir in pkgs_dirs:
        for fn in pkgs_dirs[pkgs_dir]:
            try:
                if rm_rf(os.path.join(pkgs_dir, fn)):
                    if verbose:
                        print("Removed %s" % fn)
                else:
                    if verbose:
                        print("WARNING: cannot remove, file permissions: %s" % fn)
            except (IOError, OSError) as e:
                if verbose:
                    print("WARNING: cannot remove, file permissions: %s\n%r" % (fn, e))
                else:
                    log.info("%r", e)


def find_pkgs():
    # TODO: This doesn't handle packages that have hard links to files within
    # themselves, like bin/python3.3 and bin/python3.3m in the Python package
    warnings = []

    cross_platform_st_nlink = CrossPlatformStLink()
    pkgs_dirs = defaultdict(list)
    for pkgs_dir in context.pkgs_dirs:
        if not os.path.exists(pkgs_dir):
            print("WARNING: {0} does not exist".format(pkgs_dir))
            continue
        pkgs = [i for i in listdir(pkgs_dir)
                if (isdir(join(pkgs_dir, i)) and  # only include actual packages
                    isdir(join(pkgs_dir, i, 'info')))]
        for pkg in pkgs:
            breakit = False
            for root, dir, files in walk(join(pkgs_dir, pkg)):
                for fn in files:
                    try:
                        st_nlink = cross_platform_st_nlink(join(root, fn))
                    except OSError as e:
                        warnings.append((fn, e))
                        continue
                    if st_nlink > 1:
                        # print('%s is installed: %s' % (pkg, join(root, fn)))
                        breakit = True
                        break

                if breakit:
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
        print('-' * 51)  # 40 + 1 + 10 in fmt
        print(fmt % ('Total:', human_bytes(totalsize)))
        print()

    if not context.json:
        confirm_yn(args)
    if context.json and args.dry_run:
        return

    for pkgs_dir in pkgs_dirs:
        for pkg in pkgs_dirs[pkgs_dir]:
            if verbose:
                print("removing %s" % pkg)
            rm_rf(join(pkgs_dir, pkg))


def rm_index_cache():
    from ..gateways.disk.delete import rm_rf
    from ..core.package_cache import PackageCache
    for package_cache in PackageCache.all_writable():
        rm_rf(join(package_cache.pkgs_dir, 'cache'))


def find_source_cache():
    cache_dirs = {
        'source cache': context.src_cache,
        'git cache': context.git_cache,
        'hg cache': context.hg_cache,
        'svn cache': context.svn_cache,
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
    verbose = not context.json
    if warnings:
        if verbose:
            for warning in warnings:
                print(warning, file=sys.stderr)
        return

    for cache_type in cache_dirs:
        print("%s (%s)" % (cache_type, cache_dirs[cache_type]))
        print("%-40s %10s" % ("Size:", human_bytes(cache_sizes[cache_type])))
        print()

    print("%-40s %10s" % ("Total:", human_bytes(total_size)))

    if not context.json:
        confirm_yn(args)
    if context.json and args.dry_run:
        return

    for dir in cache_dirs.values():
        print("Removing %s" % dir)
        rm_rf(dir)


def execute(args, parser):
    json_result = {
        'success': True
    }

    if args.tarballs or args.all:
        pkgs_dirs, totalsize = find_tarballs()
        first = sorted(pkgs_dirs)[0] if pkgs_dirs else ''
        json_result['tarballs'] = {
            'pkgs_dir': first,  # Backwards compabitility
            'pkgs_dirs': dict(pkgs_dirs),
            'files': pkgs_dirs[first],  # Backwards compatibility
            'total_size': totalsize
        }
        rm_tarballs(args, pkgs_dirs, totalsize, verbose=not context.json)

    if args.index_cache or args.all:
        json_result['index_cache'] = {
            'files': [join(context.pkgs_dirs[0], 'cache')]
        }
        rm_index_cache()

    if args.packages or args.all:
        pkgs_dirs, warnings, totalsize, pkgsizes = find_pkgs()
        first = sorted(pkgs_dirs)[0] if pkgs_dirs else ''
        json_result['packages'] = {
            'pkgs_dir': first,  # Backwards compatibility
            'pkgs_dirs': dict(pkgs_dirs),
            'files': pkgs_dirs[first],  # Backwards compatibility
            'total_size': totalsize,
            'warnings': warnings,
            'pkg_sizes': {i: dict(zip(pkgs_dirs[i], pkgsizes[i])) for i in pkgs_dirs},
        }
        rm_pkgs(args, pkgs_dirs,  warnings, totalsize, pkgsizes,
                verbose=not context.json)

    if args.source_cache or args.all:
        json_result['source_cache'] = find_source_cache()
        rm_source_cache(args, **json_result['source_cache'])

    if not any((args.lock, args.tarballs, args.index_cache, args.packages,
                args.source_cache, args.all)):
        raise ArgumentError("One of {--lock, --tarballs, --index-cache, --packages, "
                            "--source-cache, --all} required")

    if context.json:
        stdout_json(json_result)
