# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

"""plugin for .tar.bz2"""

import os
from logging import getLogger
from os.path import join

from ...base.constants import CONDA_PACKAGE_EXTENSION_V1
from ...common.compat import on_linux
from ...gateways.disk.delete import path_is_clean
from ..hookspec import hookimpl
from ..types import CondaPackageExtractor

log = getLogger(__name__)


def extract_tarball(
    tarball_full_path, destination_directory=None, progress_update_callback=None
):
    import conda_package_handling.api

    if destination_directory is None:
        if tarball_full_path[-8:] == CONDA_PACKAGE_EXTENSION_V1:
            destination_directory = tarball_full_path[:-8]
        else:
            destination_directory = tarball_full_path.splitext()[0]
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
        name="Conda Package",
        extensions=[".tar.bz2", ".conda"],
        extract=extract_tarball,
    )


# TODO
# add a verification/parsing function also
