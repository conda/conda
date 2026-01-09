# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

"""plugin for .tar.bz2"""

from conda.gateways.disk.create import extract_tarball

from ... import hookimpl
from ..types import CondaSupportedPkgFormats


@hookimpl
def conda_supported_extensions():
    yield CondaSupportedPkgFormats(
        name="Conda Package", extensions=[".tar.bz2", ".conda"], action=extract_tarball
    )


# TODO
# add a verification/parsing function also
