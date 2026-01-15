# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Repodata patches plugin implementation.

This module provides filtering of packages in repodata using MatchSpec,
conda's standard package query language.

Filter prefixes:
  - exclude:SPEC - remove packages matching SPEC (default if no prefix)
  - include:SPEC - keep ONLY packages matching SPEC

Configuration in .condarc:

    plugins:
      repodata_filters:
        # Exclusion filters (remove matching packages)
        - "exclude:numpy>=2.0"              # exclude numpy 2.0+
        - "exclude:*[build=*cuda*]"         # exclude CUDA builds
        - "*[timestamp=\">=2024-06-01\"]"   # exclude (default) packages from June+

        # Inclusion filters (keep ONLY matching packages)
        - 'include:*[timestamp="<2024-01-01"]'  # freeze: keep only pre-2024

Note: Operators in brackets must be quoted: *[timestamp=">=2024-01-01"]

Filter logic:
  - If ANY include filters exist, package must match at least one to be kept
  - If package matches ANY exclude filter, it's removed
  - Exclude filters are applied after include filters
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import TYPE_CHECKING

from ..common.configuration import PrimitiveParameter, SequenceParameter
from . import hookimpl
from .types import CondaRepodataPatch, CondaSetting

if TYPE_CHECKING:
    from ..models.channel import Channel
    from ..models.match_spec import MatchSpec

log = logging.getLogger(__name__)


class FilterSpecEnum(Enum):
    INCLUDE = "include"
    EXCLUDE = "exclude"

    def __str__(self) -> str:
        return f"[{self.value}]"


def parse_filter_spec(spec_str: str) -> tuple[FilterSpecEnum, MatchSpec]:
    """Parse a filter spec into (mode, matchspec_str).

    Supports prefixes:
      - "exclude:SPEC" -> (FilterSpecEnum.EXCLUDE, "SPEC")
      - "include:SPEC" -> (FilterSpecEnum.INCLUDE, "SPEC")
      - "SPEC" -> (FilterSpecEnum.EXCLUDE, "SPEC")  # default is exclude
    """
    from ..models.match_spec import MatchSpec

    spec_str = spec_str.strip()
    if spec_str.startswith("exclude:"):
        mode, spec_str = FilterSpecEnum.EXCLUDE, spec_str[8:]
    elif spec_str.startswith("include:"):
        mode, spec_str = FilterSpecEnum.INCLUDE, spec_str[8:]
    else:
        mode = FilterSpecEnum.EXCLUDE
    return mode, MatchSpec(spec_str)


def filter_packages(channel: Channel, repodata: dict) -> dict:
    """
    Filter packages from repodata based on configured MatchSpec filters.

    Supports include/exclude prefixes:
      - exclude:SPEC - remove packages matching SPEC (default)
      - include:SPEC - keep ONLY packages matching SPEC

    Logic:
      - If ANY include filters exist, package must match at least one
      - If package matches ANY exclude filter, it's removed

    Args:
        channel: The channel being processed
        repodata: The parsed repodata dictionary

    Returns:
        Modified repodata with filtered packages removed
    """
    from ..base.context import context

    # Get configuration from plugin settings
    filter_specs: list[str] = list(context.plugins.repodata_filters or [])

    if not filter_specs:
        return repodata

    # Parse filters into include/exclude lists
    include_specs: list[MatchSpec] = []
    exclude_specs: list[MatchSpec] = []

    for spec_str in filter_specs:
        try:
            mode, spec = parse_filter_spec(spec_str)
            if mode == FilterSpecEnum.INCLUDE:
                include_specs.append(spec)
            else:
                exclude_specs.append(spec)
        except Exception as e:
            log.warning(f"Invalid repodata filter '{spec_str}': {e}")

    if not include_specs and not exclude_specs:
        return repodata

    log.debug(
        f"Applying repodata filters to {channel}: "
        f"{len(include_specs)} include, {len(exclude_specs)} exclude"
    )

    # Track statistics
    total_removed = 0

    # Filter both packages and packages.conda sections
    for section, packages in repodata.items():
        if section not in ("packages", "packages.conda") or not packages:
            continue

        # Build list of packages to remove
        to_remove = []
        for fn, info in packages.items():
            should_remove = False

            # Step 1: If include filters exist, package must match at least one
            if include_specs:
                matches_include = False
                for spec in include_specs:
                    try:
                        if spec.match(info):
                            matches_include = True
                            break
                    except Exception as e:
                        log.debug(f"Error matching {fn} against include {spec}: {e}")

                if not matches_include:
                    should_remove = True
                    log.debug(f"Package {fn} doesn't match any include filter")

            # Step 2: Check exclude filters (even if already marked for removal)
            if not should_remove:
                for spec in exclude_specs:
                    try:
                        if spec.match(info):
                            should_remove = True
                            log.debug(f"Package {fn} matches exclude filter {spec}")
                            break
                    except Exception as e:
                        log.debug(f"Error matching {fn} against exclude {spec}: {e}")

            if should_remove:
                to_remove.append(fn)

        # Remove matching packages
        for fn in to_remove:
            del packages[fn]

        if to_remove:
            log.debug(f"Filtered {len(to_remove)} packages from {section}")
            total_removed += len(to_remove)

    if total_removed:
        log.info(f"Repodata filter: removed {total_removed} packages from {channel}")

    return repodata


# ============================================================================
# Plugin registration
# ============================================================================


@hookimpl
def conda_repodata_patches():
    """Register the package filter repodata patch."""
    yield CondaRepodataPatch(
        name="filter-packages",
        action=filter_packages,
    )


@hookimpl
def conda_settings():
    """Register repodata filtering settings."""
    yield CondaSetting(
        name="repodata_filters",
        description=(
            "List of MatchSpec patterns to filter packages from repodata. "
            "Prefix with 'include:' to keep only matching packages, or 'exclude:' "
            "(default) to remove matching packages. "
            "Examples: 'include:*[timestamp=\"<2024-01-01\"]', 'exclude:numpy>=2.0'"
        ),
        parameter=SequenceParameter(PrimitiveParameter("", element_type=str)),
        aliases=("repodata_filter",),
    )
