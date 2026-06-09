# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""POC: display a notice from the CONDA_NOTICE environment variable."""

import os

from ..base.constants import NoticeLevel
from . import hookimpl
from .types import CondaNotice


@hookimpl
def conda_notices():
    message = os.environ.get("CONDA_NOTICE")
    if message:
        yield CondaNotice(
            name="env-var-notice",
            message=message,
            level=NoticeLevel.INFO,
            # created_at=datetime.now(timezone.utc),
        )
