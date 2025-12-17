# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Fix task: Clean up malformed specs in pinned file."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .....base.constants import PREFIX_PINNED_FILE
from .....base.context import context
from .....cli.helpers import add_output_and_prompt_options, add_parser_prefix
from .....core.prefix_data import PrefixData
from .....exceptions import CondaError
from .....models.match_spec import MatchSpec
from .....reporters import confirm_yn
from .... import hookimpl
from ....types import CondaHealthFix

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace

SUMMARY = "Clean up invalid specs in pinned file"


def configure_parser(parser: ArgumentParser) -> None:
    """Configure parser for malformed-pinned fix task."""
    parser.description = (
        "Clean up malformed specs in the pinned file.\n\n"
        "This fix task identifies specs in the conda-meta/pinned file that "
        "reference packages not installed in the environment (possibly typos) "
        "and offers to remove them."
    )
    add_parser_prefix(parser)
    add_output_and_prompt_options(parser)


def execute(args: Namespace) -> int:
    """Execute the malformed-pinned fix task."""
    prefix_data = PrefixData.from_context()
    prefix_data.assert_environment()

    pinned_file = prefix_data.prefix_path / PREFIX_PINNED_FILE

    if not pinned_file.exists():
        print(f"No pinned file found at {pinned_file}")
        return 0

    try:
        pinned_specs = prefix_data.get_pinned_specs()
    except Exception as err:
        raise CondaError(f"Error reading pinned file: {err}")

    if not pinned_specs:
        print("Pinned file is empty.")
        return 0

    # Find specs for packages that aren't installed
    malformed = [
        spec for spec in pinned_specs if not any(prefix_data.query(spec.name))
    ]

    if not malformed:
        print("No malformed specs found in pinned file.")
        return 0

    print(f"Found {len(malformed)} potentially malformed spec(s) in {pinned_file}:")
    for spec in malformed:
        print(f"  {spec} (package not installed)")

    print()
    confirm_yn(
        "Remove these specs from the pinned file?",
        default="no",
        dry_run=context.dry_run,
    )

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
def conda_health_fixes():
    """Register the malformed-pinned fix."""
    yield CondaHealthFix(
        name="malformed-pinned",
        summary=SUMMARY,
        configure_parser=configure_parser,
        execute=execute,
    )
