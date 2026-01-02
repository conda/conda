# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Register signature verification as a post-solve plugin."""

import warnings

from .. import hookimpl
from ..types import CondaPostSolve


@hookimpl
def conda_post_solves():
    # FUTURE: conda 26.3+, remove ignore signature_verification deprecation
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r"conda\.trust(\.\w+)? is deprecated and will be removed in 26\.3\.",
            category=DeprecationWarning,
        )
        from ...trust.signature_verification import signature_verification

        yield CondaPostSolve(
            name="signature-verification",
            action=signature_verification,
        )
