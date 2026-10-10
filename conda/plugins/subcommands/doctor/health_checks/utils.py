# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Health check: Helpful shared functions for performing health checks."""

from __future__ import annotations

from logging import getLogger
from pathlib import Path

from .....common.serialize import json

logger = getLogger(__name__)


def get_specs_from_conda_meta(
    prefix: str, packages: list[str]
) -> tuple[list[str], list[str]]:
    """Get a list of specs (specified with name, version, and build) from the prefix
    matching the name of the requested packages. If the name, version or build metadata
    is incomplete, the package will be skipped.
    """
    specs = []
    skipped = []
    for stem in packages:
        try:
            metadata = json.loads(
                (Path(prefix) / "conda-meta" / f"{stem}.json").read_text()
            )
            specs.append(
                f"{metadata['name']}={metadata['version']}={metadata['build']}"
            )
        except KeyError as exc:
            logger.error(
                "Could not build an installable MatchSpec from conda-meta record; "
                "missing field %s. Skipping reinstall for %s.",
                exc,
                stem,
            )
            print(
                f"Reinstalling package {stem} failed due to missing fields in conda-meta record."
            )
            skipped.append(stem)
    return specs, skipped
