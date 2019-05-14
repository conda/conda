# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import defaultdict
import fnmatch
from logging import getLogger
from os import listdir, lstat, unlink, walk
from os.path import exists, getsize, isdir, join
import sys

from ..base.constants import CONDA_PACKAGE_EXTENSIONS, CONDA_TEMP_EXTENSION
from ..base.context import context

log = getLogger(__name__)


def find_tarballs():
    from ..core.package_cache_data import PackageCacheData
    pkgs_dirs = defaultdict(list)
    totalsize = 0
    part_ext = tuple(e + '.part' for e in CONDA_PACKAGE_EXTENSIONS)
    for package_cache in PackageCacheData.writable_caches(context.pkgs_dirs):
        pkgs_dir = package_cache.pkgs_dir
        if not isdir(pkgs_dir):
            continue
        root, _, filenames = next(walk(pkgs_dir))
        for fn in filenames:
            if fn.endswith(CONDA_PACKAGE_EXTENSIONS) or fn.endswith(part_ext):
                pkgs_dirs[pkgs_dir].append(fn)
                totalsize += getsize(join(root, fn))

    return pkgs_dirs, totalsize


def rm_tarballs(args, pkgs_dirs, totalsize, verbose=True):
    from .common import confirm_yn
    from ..gateways.disk.delete import rm_rf
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
        print('')

        for pkgs_dir in pkgs_dirs:
            print(pkgs_dir)
            print('-'*len(pkgs_dir))
            fmt = "%-40s %10s"
            for fn in pkgs_dirs[pkgs_dir]:
                size = getsize(join(pkgs_dir, fn))
                print(fmt % (fn, human_bytes(size)))
            print('')
        print('-' * 51)  # From 40 + 1 + 10 in fmt
        print(fmt % ('Total:', human_bytes(totalsize)))
        print('')

    if not context.json or not context.always_yes:
        confirm_yn()
    if context.json and args.dry_run:
        return

    for pkgs_dir in pkgs_dirs:
        for fn in pkgs_dirs[pkgs_dir]:
            try:
                if rm_rf(join(pkgs_dir, fn)):
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
    from ..gateways.disk.delete import rm_rf
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
            print('')
            fmt = "%-40s %10s"
            for pkg, pkgsize in zip(pkgs_dirs[pkgs_dir], pkgsizes[pkgs_dir]):
                print(fmt % (pkg, human_bytes(pkgsize)))
            print('')
        print('-' * 51)  # 40 + 1 + 10 in fmt
        print(fmt % ('Total:', human_bytes(totalsize)))
        print('')

    if not context.json or not context.always_yes:
        confirm_yn()
    if context.json and args.dry_run:
        return

    for pkgs_dir in pkgs_dirs:
        for pkg in pkgs_dirs[pkgs_dir]:
            if verbose:
                print("removing %s" % pkg)
            rm_rf(join(pkgs_dir, pkg))


def rm_index_cache():
    from ..gateways.disk.delete import rm_rf
    from ..core.package_cache_data import PackageCacheData
    for package_cache in PackageCacheData.writable_caches():
        rm_rf(join(package_cache.pkgs_dir, 'cache'))


def rm_rf_pkgs_dirs():
    from .common import confirm_yn
    from ..common.io import dashlist
    from ..gateways.disk.delete import rm_rf
    from ..core.package_cache_data import PackageCacheData

    writable_pkgs_dirs = tuple(
        pc.pkgs_dir for pc in PackageCacheData.writable_caches() if isdir(pc.pkgs_dir)
    )
    if not context.json or not context.always_yes:
        print("Remove all contents from the following package caches?%s"
              % dashlist(writable_pkgs_dirs))
        confirm_yn()

    for pkgs_dir in writable_pkgs_dirs:
        rm_rf(pkgs_dir)

    return writable_pkgs_dirs


def clean_tmp_files(path=None):
    if not path:
        path = sys.prefix
    for root, dirs, fns in walk(path):
        for fn in fns:
            if (fnmatch.fnmatch(fn, "*.trash") or
                    fnmatch.fnmatch(fn, "*" + CONDA_TEMP_EXTENSION)):
                file_path = join(root, fn)
                try:
                    unlink(file_path)
                except EnvironmentError:
                    log.warn("File at {} could not be cleaned up.  "
                             "It's probably still in-use.".format(file_path))

def _execute(args, parser):
    json_result = {
        'success': True
    }
    one_target_ran = False

    if args.source_cache:
        print("WARNING: 'conda clean --source-cache' is deprecated.\n"
              "    Use 'conda build purge-all' to remove source cache files.",
              file=sys.stderr)

    if args.force_pkgs_dirs:
        writable_pkgs_dirs = rm_rf_pkgs_dirs()
        json_result['pkgs_dirs'] = writable_pkgs_dirs

        # we return here because all other clean operations target individual parts of
        # package caches
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
        rm_tarballs(args, pkgs_dirs, totalsize, verbose=not (context.json or context.quiet))
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
        rm_pkgs(args, pkgs_dirs,  warnings, totalsize, pkgsizes,
                verbose=not (context.json or context.quiet))
        one_target_ran = True

    if args.all:
        clean_tmp_files(sys.prefix)
    elif args.tempfiles:
        for path in args.tempfiles:
            clean_tmp_files(path)

    if not one_target_ran:
        from ..exceptions import ArgumentError
        raise ArgumentError("At least one removal target must be given. See 'conda clean --help'.")

    return json_result


def execute(args, parser):
    from .common import stdout_json
    json_result = _execute(args, parser)
    if context.json:
        stdout_json(json_result)
