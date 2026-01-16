# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

"""plugin for .tar.bz2"""

from conda.gateways.disk.create import extract_tarball

from ..hookspec import hookimpl
from ..types import CondaPkgExtractors


@hookimpl
def conda_pkg_extractors():
    yield CondaPkgExtractors(
        name="Conda Package",
        extensions=[".tar.bz2", ".conda"],
        extractor=extract_tarball,
    )


# TODO
# add a verification/parsing function also
