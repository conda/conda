# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
conda._ng.cli.main_install — next-generation ``conda install`` stub.

This module is selected when ``ng`` appears in ``context.experimental``
and the user runs ``conda install``.  The first iteration intentionally
delegates to the classic implementation; future iterations will replace
the body of ``execute`` with ng-native logic.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace

log = logging.getLogger(__name__)


def execute(args: Namespace, parser: ArgumentParser) -> int:
    """Entry point for ``conda install`` under the ng experimental flag.

    .. note::
        **Non-operational stub.**  This function currently delegates to the
        classic ``conda.cli.main_install.execute`` implementation.  It exists
        solely to prove that the routing infrastructure works end-to-end.
        Replace or extend this body in subsequent iterations.
    """
    log.debug(
        "conda._ng.cli.main_install.execute called (stub — delegating to classic)"
    )

    from conda.cli.main_install import execute as _classic_execute

    return _classic_execute(args, parser)
