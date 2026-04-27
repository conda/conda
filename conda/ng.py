# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
conda.ng — convenience entry-point shim for the next-generation backend.

Usage
-----
Run directly as a module to opt into the ``ng`` experimental code path
without modifying any configuration files::

    python -m conda.ng <subcommand> [options]

This is equivalent to::

    CONDA_EXPERIMENTAL=ng conda <subcommand> [options]

How it works
------------
The shim injects ``ng`` into the ``CONDA_EXPERIMENTAL`` environment variable
(preserving any values already present) before handing control to the
standard ``conda.cli.main:main`` entry point.  All argument parsing,
plugin loading, and dispatch logic therefore runs exactly as it would for a
normal ``conda`` invocation — the only difference is that the ``ng`` flag is
guaranteed to be active.
"""

from __future__ import annotations

import os
import sys


def _inject_ng_experimental() -> None:
    """
    Ensure ``ng`` is present in ``CONDA_EXPERIMENTAL`` before we start.
    """
    current = os.environ.get("CONDA_EXPERIMENTAL", "")
    values = [v.strip() for v in current.split(",") if v.strip()]
    if "ng" not in values:
        values.append("ng")
    os.environ["CONDA_EXPERIMENTAL"] = ",".join(values)


def main() -> int:
    """Shim entry point: inject the ng flag and delegate to conda.cli.main."""
    _inject_ng_experimental()
    from conda.cli.main import main as _main

    return _main()


if __name__ == "__main__":
    sys.exit(main())
