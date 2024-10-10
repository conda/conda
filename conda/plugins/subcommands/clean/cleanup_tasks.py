# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Backend logic implementation for `conda clean`."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from ... import hookimpl
from ...types import CondaCleanupTask

if TYPE_CHECKING:
    from typing import Iterable


def get_pkgs_dirs(arg: bool = True) -> Iterable[Path]:
    from ....core.package_cache_data import PackageCacheData

    return (
        pkgs_dir
        for cache in PackageCacheData.writable_caches()
        if (pkgs_dir := Path(cache.pkgs_dir)).is_dir()
    )


def get_index_cache(arg: bool = True) -> Iterable[Path]:
    # caches are directories in pkgs_dir
    return (
        cache for pkgs_dir in get_pkgs_dirs() if (cache := pkgs_dir / "cache").is_dir()
    )


def get_unused_packages(arg: bool = True) -> dict[Path, Iterable[Path]]:
    return {pkgs_dir: _get_unused_packages(pkgs_dir) for pkgs_dir in get_pkgs_dirs()}


def _get_unused_packages(prefix: Path) -> Iterable[Path]:
    from ....gateways.disk.test import has_hardlinks

    for path in prefix.iterdir():
        if not (path / "info").is_dir():
            # pkgs have an info directory
            continue
        elif has_hardlinks(path):
            # ignore packages with hardlinks
            # TODO: This doesn't handle packages that have hard links to files within
            # themselves, like bin/python3.3 and bin/python3.3m in the Python package
            continue

        yield path


def get_tarballs(arg: bool = True) -> dict[Path, Iterable[Path]]:
    return {pkgs_dir: tuple(_get_tarballs(pkgs_dir)) for pkgs_dir in get_pkgs_dirs()}


def _get_tarballs(prefix: Path) -> Iterable[Path]:
    from ....base.constants import CONDA_PACKAGE_EXTENSIONS, CONDA_PACKAGE_PARTS

    for path in prefix.iterdir():
        if path.is_dir():
            # tarballs are files in pkgs_dir
            continue
        elif not path.name.endswith((*CONDA_PACKAGE_EXTENSIONS, *CONDA_PACKAGE_PARTS)):
            # tarballs also end in .tar.bz2, .conda, .tar.bz2.part, or .conda.part
            continue

        yield path


def get_tempfiles(prefixes: Iterable[Path] | None) -> Iterable[Path]:
    from ....base.constants import CONDA_TEMP_EXTENSIONS

    for prefix in sorted(set(prefixes or {Path(sys.prefix)})):
        if not prefix.is_dir():
            continue

        # tempfiles are files in path
        for path in prefix.iterdir():
            if path.is_dir():
                # iteratively search directories
                yield from get_tempfiles([path])
            elif path.name.endswith(CONDA_TEMP_EXTENSIONS):
                # tempfiles also end in .c~ or .trash
                yield path


def get_logfiles(arg: bool = True) -> Iterable[Path]:
    from ....base.constants import CONDA_LOGS_DIR

    for pkgs_dir in get_pkgs_dirs():
        # .logs are directories in pkgs_dir
        if not (prefix := pkgs_dir / CONDA_LOGS_DIR).is_dir():
            continue

        for path in prefix.iterdir():
            if not path.is_file():
                # logfiles are files in .logs
                continue
            else:
                yield path


@hookimpl
def conda_cleanup_tasks() -> Iterable[CondaCleanupTask]:
    from ....cli.actions import ExtendConstAction

    yield CondaCleanupTask(
        name="force_pkgs_dirs",
        flags=["-f", "--force-pkgs-dirs"],
        help=(
            "Remove *all* writable package caches. This option is not included with the --all "
            "flag. WARNING: This will break environments with packages installed using symlinks "
            "back to the package cache."
        ),
        action=get_pkgs_dirs,
        all=False,
    )

    yield CondaCleanupTask(
        name="tarballs",
        flags=["-t", "--tarballs"],
        help="Remove cached package tarballs.",
        action=get_tarballs,
    )
    yield CondaCleanupTask(
        name="index_cache",
        flags=["-i", "--index-cache"],
        help="Remove index cache.",
        action=get_index_cache,
    )
    yield CondaCleanupTask(
        name="packages",
        flags=["-p", "--packages"],
        help=(
            "Remove unused packages from writable package caches. "
            "WARNING: This does not check for packages installed using "
            "symlinks back to the package cache."
        ),
        action=get_unused_packages,
    )
    yield CondaCleanupTask(
        name="tempfiles",
        flags=[
            "-c",  # for tempfile extension (.c~)
            "--tempfiles",
        ],
        help=(
            "Remove temporary files that could not be deleted earlier due to being in-use.  "
            "The argument for the --tempfiles flag is a path (or list of paths) to the "
            "environment(s) where the tempfiles should be found and removed."
        ),
        add_argument_kwargs={
            "const": Path(sys.prefix),
            "action": ExtendConstAction,
            "type": Path,
        },
        action=get_tempfiles,
    )
    yield CondaCleanupTask(
        name="logfiles",
        flags=["-l", "--logfiles"],
        help="Remove log files.",
        action=get_logfiles,
    )
