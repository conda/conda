# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Preview feature: env-setup.

Scaffolding for the upcoming Rich CLI and runner facade for create/install/update/remove.
Currently non-operational — all CLI entry points raise ``OperationNotAllowed``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from conda.base.context import Context

PREVIEW_LABEL = "env-setup"


def register(context: Context) -> None:
    """Called after the final ``context.__init__()`` when this preview is enabled.

    Currently a no-op stub. Future implementations will use this hook to register
    additional plugin hooks, patch context state, or perform other one-time setup.
    """
