# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
from os import lstat, walk
from os.path import isdir, join
from typing import Any, Dict, Iterable, List, Optional, Tuple
import sys

from ..base.constants import CONDA_PACKAGE_EXTENSIONS, CONDA_TEMP_EXTENSIONS
from ..base.context import context

log = getLogger(__name__)
_EXTS = (*CONDA_PACKAGE_EXTENSIONS, *(f"{e}.part" for e in CONDA_PACKAGE_EXTENSIONS))


def _getsize(*parts: str, warnings: Optional[List[Tuple[str, Exception]]] = None) -> int:
    path = join(*parts)
    try:
        stat = lstat(path)
    except OSError as e:
        if warnings is None:
            raise
        warnings.append((path, e))

    # TODO: This doesn't handle packages that have hard links to files within
    # themselves, like bin/python3.3 and bin/python3.3m in the Python package
    if stat.st_nlink > 1:
        raise NotImplementedError

    return stat.st_size


def find_tarballs() -> Dict[str, Any]:
    warnings: List[Tuple[str, Exception]] = []
    pkg_sizes: Dict[str, Dict[str, int]] = {}
    for pkgs_dir in find_pkgs_dirs():
        # tarballs are files in pkgs_dir
        _, _, tars = next(walk(pkgs_dir))
        for tar in tars:
            # tarballs also end in .tar.bz2, .conda, .tar.bz2.part, or .conda.part
            if not tar.endswith(_EXTS):
                continue

            # get size
            try:
                size = _getsize(pkgs_dir, tar, warnings=warnings)
            except NotImplementedError:
                pass
            else:
                pkg_sizes.setdefault(pkgs_dir, {})[tar] = size

    return {
        "warnings": warnings,
        "pkg_sizes": pkg_sizes,
        "pkgs_dirs": {pkgs_dir: tuple(pkgs) for pkgs_dir, pkgs in pkg_sizes.items()},
        "total_size": sum(sum(pkgs.values()) for pkgs in pkg_sizes.values()),
    }


def rm_tarballs(args, pkgs_dirs, warnings, total_size, pkg_sizes, verbose=True):
    from .common import confirm_yn
    from ..gateways.disk.delete import rm_rf
    from ..utils import human_bytes

    if not any(pkgs_dirs[i] for i in pkgs_dirs):
        if verbose:
            print("There are no tarballs to remove")
        return

    if verbose:
        print("Will remove the following tarballs:")
        print('')

        for pkgs_dir, pkgs in pkg_sizes.items():
            print(pkgs_dir)
            print('-'*len(pkgs_dir))
            fmt = "%-40s %10s"
            for fn, size in pkgs.items():
                print(fmt % (fn, human_bytes(size)))
            print("")
        print("-" * 51)  # From 40 + 1 + 10 in fmt
        print(fmt % ("Total:", human_bytes(total_size)))
        print("")

    if args.dry_run:
        return
    if not context.json or not context.always_yes:
        confirm_yn()

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


def find_pkgs() -> Dict[str, Any]:
    warnings: List[Tuple[str, Exception]] = []
    pkg_sizes: Dict[str, Dict[str, int]] = {}
    for pkgs_dir in find_pkgs_dirs():
        # pkgs are directories in pkgs_dir
        _, pkgs, _ = next(walk(pkgs_dir))
        for pkg in pkgs:
            # pkgs also have an info directory
            if not isdir(join(pkgs_dir, pkg, "info")):
                continue

            # get size
            try:
                size = sum(
                    _getsize(root, file, warnings=warnings)
                    for root, _, files in walk(join(pkgs_dir, pkg))
                    for file in files
                )
            except NotImplementedError:
                pass
            else:
                pkg_sizes.setdefault(pkgs_dir, {})[pkg] = size

    return {
        "warnings": warnings,
        "pkg_sizes": pkg_sizes,
        "pkgs_dirs": {pkgs_dir: tuple(pkgs) for pkgs_dir, pkgs in pkg_sizes.items()},
        "total_size": sum(sum(pkgs.values()) for pkgs in pkg_sizes.values()),
    }


def rm_pkgs(args, pkgs_dirs, warnings, total_size, pkg_sizes, verbose=True):
    from .common import confirm_yn
    from ..gateways.disk.delete import rm_rf
    from ..utils import human_bytes

    if verbose and warnings:
        for fn, exception in warnings:
            print(exception)

    if not any(pkgs_dirs[i] for i in pkgs_dirs):
        if verbose:
            print("There are no unused packages to remove")
        return

    if verbose:
        print("Will remove the following packages:")
        for pkgs_dir, pkgs in pkg_sizes.items():
            print(pkgs_dir)
            print('-' * len(pkgs_dir))
            print('')
            fmt = "%-40s %10s"
            for pkg, pkgsize in pkgs.items():
                print(fmt % (pkg, human_bytes(pkgsize)))
            print("")
        print("-" * 51)  # 40 + 1 + 10 in fmt
        print(fmt % ("Total:", human_bytes(total_size)))
        print("")

    if args.dry_run:
        return
    if not context.json or not context.always_yes:
        confirm_yn()

    for pkgs_dir in pkgs_dirs:
        for pkg in pkgs_dirs[pkgs_dir]:
            if verbose:
                print("removing %s" % pkg)
            rm_rf(join(pkgs_dir, pkg))


def find_index_cache() -> List[str]:
    files = []
    for pkgs_dir in find_pkgs_dirs():
        # caches are directories in pkgs_dir
        path = join(pkgs_dir, "cache")
        if isdir(path):
            files.append(path)
    return files


def find_pkgs_dirs() -> List[str]:
    from ..core.package_cache_data import PackageCacheData

    return [pc.pkgs_dir for pc in PackageCacheData.writable_caches() if isdir(pc.pkgs_dir)]


def find_tempfiles(paths: Iterable[str]) -> List[str]:
    tempfiles = []
    for path in sorted(set(paths or [sys.prefix])):
        # tempfiles are files in path
        for root, _, files in walk(path):
            for file in files:
                # tempfiles also end in .c~ or .trash
                if not file.endswith(CONDA_TEMP_EXTENSIONS):
                    continue

                tempfiles.append(join(root, file))

    return tempfiles


def rm_items(args, items: List[str], verbose: bool, name: str) -> None:
    from .common import confirm_yn
    from ..gateways.disk.delete import rm_rf

    if not items:
        if verbose:
            print(f"There are no {name} to remove.")
        return

    if verbose:
        if args.verbosity:
            print(f"Will remove the following {name}:")
            for item in items:
                print(f"  - {item}")
            print()
        else:
            print(f"Will remove {len(items)} {name}.")

    if args.dry_run:
        return
    if not context.json or not context.always_yes:
        confirm_yn()

    for item in items:
        rm_rf(item)


def _execute(args, parser):
    json_result = {"success": True}
    verbose = not (context.json or context.quiet)

    if args.force_pkgs_dirs:
        json_result["pkgs_dirs"] = pkgs_dirs = find_pkgs_dirs()
        rm_items(args, pkgs_dirs, verbose=verbose, name="package cache(s)")

        # we return here because all other clean operations target individual parts of
        # package caches
        return json_result

    if not (args.all or args.tarballs or args.index_cache or args.packages or args.tempfiles):
        from ..exceptions import ArgumentError

        raise ArgumentError("At least one removal target must be given. See 'conda clean --help'.")

    if args.tarballs or args.all:
        json_result["tarballs"] = tars = find_tarballs()
        rm_tarballs(args, **tars, verbose=verbose)

    if args.index_cache or args.all:
        cache = find_index_cache()
        json_result["index_cache"] = {"files": cache}
        rm_items(args, cache, verbose=verbose, name="index cache(s)")

    if args.packages or args.all:
        json_result["packages"] = pkgs = find_pkgs()
        rm_pkgs(args, **pkgs, verbose=verbose)

    if args.tempfiles or args.all:
        json_result["tempfiles"] = tmps = find_tempfiles(args.tempfiles)
        rm_items(args, tmps, verbose=verbose, name="tempfile(s)")

    return json_result


def execute(args, parser):
    from .common import stdout_json
    json_result = _execute(args, parser)
    if context.json:
        stdout_json(json_result)
    if args.dry_run:
        from ..exceptions import DryRunExit

        raise DryRunExit
