# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Health check: Pinned file format."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .....base.constants import OK_MARK, PREFIX_PINNED_FILE, X_MARK
from .....common.io import dashlist
from .....core.prefix_data import PrefixData
from .....models.match_spec import MatchSpec
from .... import hookimpl
from ....types import CondaHealthCheck

if TYPE_CHECKING:
    from argparse import Namespace
    from collections.abc import Iterable

    from ....types import ConfirmCallback


def find_malformed_pinned_specs(prefix_data: PrefixData) -> list[MatchSpec]:
    """Find pinned specs that reference packages not installed in the environment.

    Returns a list of MatchSpec objects for packages that might be typos.
    """
    try:
        pinned_specs = prefix_data.get_pinned_specs()
    except Exception:
        return []

    if not pinned_specs:
        return []

    return [
        pinned for pinned in pinned_specs if not any(prefix_data.query(pinned.name))
    ]


def pinned_well_formatted_check(prefix: str, verbose: bool) -> None:
    """Health check action: Check pinned file format."""
    prefix_data = PrefixData(prefix_path=prefix)
    pinned_file = prefix_data.prefix_path / PREFIX_PINNED_FILE

    try:
        pinned_specs = prefix_data.get_pinned_specs()
    except OSError as err:
        print(f"{X_MARK} Unable to open pinned file at {pinned_file}:\n\t{err}")
        return
    except Exception as err:
        print(
            f"{X_MARK} An error occurred trying to read pinned file at {pinned_file}:\n\t{err}"
        )
        return

    if not pinned_specs:
        print(f"{OK_MARK} No pinned specs found in {pinned_file}.")
        return

    maybe_malformed = find_malformed_pinned_specs(prefix_data)

    if maybe_malformed:
        print(f"{X_MARK} The following specs in {pinned_file} are maybe malformed:")
        print(dashlist((spec.name for spec in maybe_malformed), indent=4))
        return

    print(f"{OK_MARK} The pinned file in {pinned_file} seems well formatted.")


def fix_malformed_pinned(prefix: str, args: Namespace, confirm: ConfirmCallback) -> int:
    """Clean up malformed specs in pinned file."""
    prefix_data = PrefixData(prefix)
    pinned_file = Path(prefix) / PREFIX_PINNED_FILE

    if not pinned_file.exists():
        print(f"No pinned file found at {pinned_file}")
        return 0

    malformed = find_malformed_pinned_specs(prefix_data)

    if not malformed:
        print("No malformed specs found in pinned file.")
        return 0

    print(f"Found {len(malformed)} potentially malformed spec(s) in {pinned_file}:")
    for spec in malformed:
        print(f"  {spec} (package not installed)")

    print()
    confirm("Remove these specs from the pinned file?")

    # Read the current file and filter out malformed specs
    malformed_names = {spec.name for spec in malformed}
    lines = pinned_file.read_text().splitlines()
    new_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue

        # Parse the spec to get the name
        try:
            spec = MatchSpec(stripped)
            if spec.name not in malformed_names:
                new_lines.append(line)
            else:
                print(f"Removing: {stripped}")
        except Exception:
            # Keep lines we can't parse
            new_lines.append(line)

    # Write back
    pinned_file.write_text("\n".join(new_lines) + "\n" if new_lines else "")
    print(f"Updated {pinned_file}")
    return 0


@hookimpl
def conda_health_checks() -> Iterable[CondaHealthCheck]:
    """Register the pinned file health check."""
    yield CondaHealthCheck(
        name="pinned",
        action=pinned_well_formatted_check,
        fixer=fix_malformed_pinned,
        summary="Validate format of the pinned file",
        fix="Remove invalid specs from pinned file",
    )
