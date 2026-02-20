# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

"""Package extractor plugin for .conda and .tar.bz2 formats."""

from __future__ import annotations

import os
from logging import getLogger
from os.path import join
from typing import TYPE_CHECKING

from ...common.compat import on_linux
from ...gateways.disk.delete import path_is_clean
from ..hookspec import hookimpl
from ..types import CondaPackageExtractor

if TYPE_CHECKING:
    from ...common.path import PathType

log = getLogger(__name__)


def extract_conda_or_tarball(
    tarball_full_path: PathType,
    destination_directory: PathType,
) -> None:
    """
    Extract a .conda or .tar.bz2 package to the specified destination.

    :param tarball_full_path: Path to the package archive.
    :param destination_directory: Directory to extract the package contents to.
    """
    import conda_package_handling.api

    # Convert PathType to string for conda_package_handling compatibility
    tarball_full_path = os.fspath(tarball_full_path)
    destination_directory = os.fspath(destination_directory)

    log.debug("extracting %s\n  to %s", tarball_full_path, destination_directory)

    # the most common reason this happens is due to hard-links, windows thinks
    #    files in the package cache are in-use. rm_rf should have moved them to
    #    have a .conda_trash extension though, so it's ok to just write into
    #    the same existing folder.
    if not path_is_clean(destination_directory):
        log.debug(
            "package folder %s was not empty, but we're writing there.",
            destination_directory,
        )

    conda_package_handling.api.extract(
        tarball_full_path, dest_dir=destination_directory
    )

    if hasattr(conda_package_handling.api, "THREADSAFE_EXTRACT"):
        return  # indicates conda-package-handling 2.x, which implements --no-same-owner

    if on_linux and os.getuid() == 0:  # pragma: no cover
        # When extracting as root, tarfile will by restore ownership
        # of extracted files.  However, we want root to be the owner
        # (our implementation of --no-same-owner).
        for root, dirs, files in os.walk(destination_directory):
            for fn in files:
                p = join(root, fn)
                os.lchown(p, 0, 0)


@hookimpl
def conda_package_extractors():
    yield CondaPackageExtractor(
        name="conda-package",
        extensions=[".tar.bz2", ".conda"],
        extract=extract_conda_or_tarball,
    )
