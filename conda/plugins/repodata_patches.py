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

Also provides a `conda repodata-filter` subcommand to inspect filters:
  - conda repodata-filter --stats      # show filter statistics
  - conda repodata-filter --list       # list configured filters
  - conda repodata-filter --preview    # preview filtered packages
"""

from __future__ import annotations

import logging
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from ..common.configuration import PrimitiveParameter, SequenceParameter
from ..common.serialize import json
from . import hookimpl
from .types import CondaRepodataPatch, CondaSetting, CondaSubcommand

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace

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
# Subcommand implementation
# ============================================================================


def configure_parser(parser: ArgumentParser) -> None:
    """Configure the repodata-filter subcommand parser."""
    parser.add_argument(
        "--list",
        dest="list_filters",
        action="store_true",
        help="List configured repodata filters.",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show statistics of original vs filtered repodata.",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Preview which packages would be filtered (limited output).",
    )
    parser.add_argument(
        "--preview-limit",
        type=int,
        default=20,
        metavar="N",
        help="Maximum packages to show in preview (default: 20).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Save patched repodata.json to provided path.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format.",
    )


def repodata_filter_action(args: Namespace) -> int | None:
    """Execute the repodata-filter subcommand."""
    from ..base.constants import REPODATA_FN
    from ..base.context import context
    from ..gateways.repodata import (
        CondaRepoInterface,
        RepodataFetch,
        cache_fn_url,
        create_cache_dir,
    )
    from ..models.channel import Channel, all_channel_urls

    # Get configured filters from plugin settings
    filter_specs: list[str] = list(context.plugins.repodata_filters or [])

    # Handle --list
    if args.list_filters:
        if args.json:
            parsed = []
            for spec in filter_specs:
                mode, matchspec = parse_filter_spec(spec)
                parsed.append({"mode": mode, "spec": matchspec, "raw": spec})
            print(json.dumps({"repodata_filters": parsed}))
        else:
            if filter_specs:
                print("Configured repodata filters:")
                for i, spec in enumerate(filter_specs, 1):
                    mode, spec = parse_filter_spec(spec)
                    print(f"  {i}. {mode} {spec}")
            else:
                print("No repodata filters configured.")
                print("\nTo configure filters, add to your .condarc:")
                print("  plugins:")
                print("    repodata_filters:")
                print(
                    "      - 'include:*[timestamp=\"<2024-01-01\"]'  # freeze to date"
                )
                print(
                    '      - "exclude:numpy>=2.0"                  # exclude specific'
                )
        return 0

    # Get channel URLs from context (already validated via context.channels)
    channel_urls = all_channel_urls(context.channels)

    results = []

    for channel in map(Channel, channel_urls):
        repodata_fetch = RepodataFetch(
            cache_path_base=Path(
                create_cache_dir(),
                cache_fn_url(channel.url(with_credentials=True), REPODATA_FN),
            ).with_suffix(""),
            channel=channel,
            repodata_fn=REPODATA_FN,
            repo_interface_cls=CondaRepoInterface,
        )

        # Fetch original (unpatched) repodata
        original, _ = repodata_fetch.fetch_latest()
        if isinstance(original, str):
            original = json.loads(original)

        # Fetch patched repodata (applies all repodata_patches including our filter)
        patched, _ = repodata_fetch.fetch_latest_parsed()

        # Compare original vs patched to find what was removed
        removed_packages: list[dict] = []
        for section in ("packages", "packages.conda"):
            original_pkgs = set(original.get(section, {}).keys())
            patched_pkgs = set(patched.get(section, {}).keys())
            removed_fns = original_pkgs - patched_pkgs

            for fn in removed_fns:
                info = original[section][fn]
                removed_packages.append(
                    {
                        "filename": fn,
                        "name": info.get("name"),
                        "version": info.get("version"),
                        "build": info.get("build"),
                    }
                )

        results.append(
            {
                "channel": str(channel),
                "subdir": channel.subdir,
                "original": original,
                "patched": patched,
                "removed_packages": removed_packages,
            }
        )

    # Handle output modes
    if args.json:
        output_data = []
        for r in results:
            output_data.append(
                {
                    "channel": r["channel"],
                    "subdir": r["subdir"],
                    "original_packages": len(r["original"].get("packages", {})),
                    "original_conda_packages": len(
                        r["original"].get("packages.conda", {})
                    ),
                    "patched_packages": len(r["patched"].get("packages", {})),
                    "patched_conda_packages": len(
                        r["patched"].get("packages.conda", {})
                    ),
                    "removed_count": len(r["removed_packages"]),
                }
            )
        print(json.dumps(output_data))
        return 0

    if args.stats:
        for r in results:
            print(f"\n{'=' * 60}")
            print(f"Channel: {r['channel']}")
            print(f"{'=' * 60}")

            orig_pkgs = len(r["original"].get("packages", {}))
            orig_conda = len(r["original"].get("packages.conda", {}))
            patched_pkgs = len(r["patched"].get("packages", {}))
            patched_conda = len(r["patched"].get("packages.conda", {}))

            print(f"{'Section':<20} {'Original':>12} {'Patched':>12} {'Removed':>12}")
            print("-" * 60)
            print(
                f"{'packages':<20} {orig_pkgs:>12} {patched_pkgs:>12} {orig_pkgs - patched_pkgs:>12}"
            )
            print(
                f"{'packages.conda':<20} {orig_conda:>12} {patched_conda:>12} {orig_conda - patched_conda:>12}"
            )
            print("-" * 60)
            total_orig = orig_pkgs + orig_conda
            total_patched = patched_pkgs + patched_conda
            print(
                f"{'TOTAL':<20} {total_orig:>12} {total_patched:>12} {total_orig - total_patched:>12}"
            )
        return 0

    if args.preview:
        for r in results:
            print(f"\n{'=' * 60}")
            print(f"Channel: {r['channel']}")
            print(
                f"Packages removed by repodata patches ({len(r['removed_packages'])} total):"
            )
            print(f"{'=' * 60}")

            shown = r["removed_packages"][: args.preview_limit]
            for pkg in shown:
                print(f"  - {pkg['name']}-{pkg['version']}-{pkg['build']}")

            remaining = len(r["removed_packages"]) - len(shown)
            if remaining > 0:
                print(
                    f"\n  ... and {remaining} more (use --preview-limit to show more)"
                )
        return 0

    if args.output:
        if len(results) == 1:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(results[0]["patched"]))
            print(f"Patched repodata written to: {args.output}")
        else:
            for r in results:
                channel_obj = Channel(r["channel"])
                path = args.output / channel_obj.name / channel_obj.subdir / REPODATA_FN
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(r["patched"]))
                print(f"Patched repodata written to: {path}")
        return 0

    # Default: show summary
    print("Repodata Patch Summary")
    print("=" * 60)
    print(f"Configured filters: {len(filter_specs)}")
    for spec in filter_specs:
        print(f"  - {spec}")
    print()

    for r in results:
        total_removed = len(r["removed_packages"])
        print(f"{r['channel']}: {total_removed} packages removed by patches")

    print()
    print("Use --stats for detailed statistics")
    print("Use --preview to see which packages were removed")

    return 0


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
def conda_subcommands():
    """Register the repodata-filter subcommand."""
    yield CondaSubcommand(
        name="repodata-filter",
        summary="Inspect and preview repodata filtering based on configured MatchSpec patterns.",
        action=repodata_filter_action,
        configure_parser=configure_parser,
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
