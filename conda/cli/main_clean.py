# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import defaultdict
from logging import getLogger
from os import listdir, lstat, walk
from os.path import getsize, isdir, join, exists
import sys

from .._vendor.toolz import concatv
from ..base.constants import CONDA_TARBALL_EXTENSION
from ..base.context import context

log = getLogger(__name__)


def find_tarballs():
    from ..core.package_cache_data import PackageCacheData
    pkgs_dirs = defaultdict(list)
    totalsize = 0
    part_ext = CONDA_TARBALL_EXTENSION + '.part'
    for package_cache in PackageCacheData.writable_caches(context.pkgs_dirs):
        pkgs_dir = package_cache.pkgs_dir
        if not isdir(pkgs_dir):
            continue
        root, _, filenames = next(walk(pkgs_dir))
        for fn in filenames:
            if fn.endswith(CONDA_TARBALL_EXTENSION) or fn.endswith(part_ext):
                pkgs_dirs[pkgs_dir].append(fn)
                totalsize += getsize(join(root, fn))

    return pkgs_dirs, totalsize


def clean_all_trash(verbose=True):
    from ..core.envs_manager import list_all_known_prefixes
    from ..gateways.disk.delete import _delete_trash_dirs
    from ..gateways.disk.link import lexists

    trash_dirs = (join(prefix, '.trash') for prefix in
                  concatv(list_all_known_prefixes(), context.pkgs_dirs))
    trash_dirs = (td for td in trash_dirs if lexists(td))

    for trash_dir in trash_dirs:
        if verbose:
            print("Removing rash directory:", trash_dir)
        _delete_trash_dirs(trash_dirs, ignore_errors=False)

    return trash_dirs


def rm_tarballs(args, pkgs_dirs, totalsize, verbose=True):
    from .common import confirm_yn
    from ..gateways.disk.delete import rm_rf_queued
    from ..utils import human_bytes

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

    if not context.json or not context.always_yes:
        confirm_yn()
    if context.json and args.dry_run:
        return

    for pkgs_dir in pkgs_dirs:
        for fn in pkgs_dirs[pkgs_dir]:
            try:
                if rm_rf_queued(join(pkgs_dir, fn)):
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

    from ..gateways.disk.link import CrossPlatformStLink
    cross_platform_st_nlink = CrossPlatformStLink()
    pkgs_dirs = defaultdict(list)
    for pkgs_dir in context.pkgs_dirs:
        if not exists(pkgs_dir):
            if not context.json:
                print("WARNING: {0} does not exist".format(pkgs_dir))
            continue
        pkgs = [i for i in listdir(pkgs_dir) if isdir(join(pkgs_dir, i, 'info'))]
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


def rm_pkgs(args, pkgs_dirs, warnings, totalsize, pkgsizes, verbose=True):
    from .common import confirm_yn
    from ..gateways.disk.delete import rm_rf_queued
    from ..utils import human_bytes
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

    if not context.json or not context.always_yes:
        confirm_yn()
    if context.json and args.dry_run:
        return

    for pkgs_dir in pkgs_dirs:
        for pkg in pkgs_dirs[pkgs_dir]:
            if verbose:
                print("removing %s" % pkg)
            rm_rf_queued(join(pkgs_dir, pkg))


def rm_index_cache():
    from ..core.package_cache_data import PackageCacheData
    from ..gateways.disk.delete import rm_rf_queued
    for package_cache in PackageCacheData.writable_caches():
        rm_rf_queued(join(package_cache.pkgs_dir, 'cache'))


def rm_rf_pkgs_dirs(verbose=True):
    from .common import confirm_yn
    from ..common.io import dashlist
    from ..gateways.disk.delete import rm_rf_queued
    from ..core.package_cache_data import PackageCacheData

    writable_pkgs_dirs = tuple(
        pc.pkgs_dir for pc in PackageCacheData.writable_caches() if isdir(pc.pkgs_dir)
    )
    if not context.json or not context.always_yes:
        print("Remove all contents from the following package caches?%s"
              % dashlist(writable_pkgs_dirs))
        confirm_yn()

    for pkgs_dir in writable_pkgs_dirs:
        if verbose:
            print("Removing %s" % pkgs_dir)
        rm_rf_queued(pkgs_dir)

    return writable_pkgs_dirs


def _execute(args, parser):
    from ..gateways.disk.delete import rm_rf_queued

    json_result = {
        'success': True
    }
    one_target_ran = False
    verbose = not (context.json or context.quiet)

    if args.source_cache:
        print("WARNING: 'conda clean --source-cache' is deprecated.\n"
              "    Use 'conda build purge-all' to remove source cache files.",
              file=sys.stderr)

    if args.force_pkgs_dirs:
        writable_pkgs_dirs = rm_rf_pkgs_dirs(verbose=verbose)
        json_result['pkgs_dirs'] = writable_pkgs_dirs

        # we return here because all other clean operations target individual parts of
        # package caches
        if args.all or args.trash:
            json_result['trash_dirs'] = clean_all_trash(verbose=verbose)
        rm_rf_queued.flush()
        return json_result

    if args.tarballs or args.all:
        pkgs_dirs, totalsize = find_tarballs()
        first = sorted(pkgs_dirs)[0] if pkgs_dirs else ''
        json_result['tarballs'] = {
            'pkgs_dir': first,  # Backwards compatibility
            'pkgs_dirs': dict(pkgs_dirs),
            'files': pkgs_dirs[first],  # Backwards compatibility
            'total_size': totalsize
        }
        rm_tarballs(args, pkgs_dirs, totalsize, verbose=verbose)
        one_target_ran = True

    if args.index_cache or args.all:
        json_result['index_cache'] = {
            'files': [join(context.pkgs_dirs[0], 'cache')]
        }
        rm_index_cache()
        one_target_ran = True

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
        rm_pkgs(args, pkgs_dirs,  warnings, totalsize, pkgsizes, verbose=verbose)
        one_target_ran = True

    if args.all or args.trash:
        clean_all_trash()
    rm_rf_queued.flush()

    if not one_target_ran:
        from ..exceptions import ArgumentError
        raise ArgumentError("At least one removal target must be given. See 'conda clean --help'.")

    return json_result


def execute(args, parser):
    from .common import stdout_json
    json_result = _execute(args, parser)
    if context.json:
        stdout_json(json_result)
