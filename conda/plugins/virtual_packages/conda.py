# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Expose conda version."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .. import hookimpl
from ..types import CondaVirtualPackage

if TYPE_CHECKING:
    from collections.abc import Iterable


@hookimpl
def conda_virtual_packages() -> Iterable[CondaVirtualPackage]:
    from ... import __version__

    # 1: __conda==VERSION=0 (always exported)
    yield CondaVirtualPackage(
        name="conda",
        version=__version__,
        build=None,
        # override_entity=None,  # no override allowed
    )
