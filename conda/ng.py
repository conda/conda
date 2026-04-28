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
The shim injects ``ng`` into the ``experimental`` context setting (preserving
any values already present) by reinitialising the context object directly,
before handing control to the standard ``conda.cli.main:main`` entry point.
All argument parsing, plugin loading, and dispatch logic therefore runs exactly
as it would for a normal ``conda`` invocation — the only difference is that
the ``ng`` flag is guaranteed to be active.
"""

from __future__ import annotations

import sys
from argparse import Namespace
from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator


@contextmanager
def _inject_ng_experimental() -> Generator[None, None, None]:
    """
    Context manager that ensures ``ng`` is present in ``context.experimental``.

    On entry the context is reinitialised with ``ng`` merged into any
    pre-existing experimental values.  On exit the context is restored to its
    original state.
    """
    from conda.base.context import context

    # Capture the current experimental values so we can restore them later.
    original_experimental = list(context.experimental)

    # Build the new list, preserving existing values and adding "ng" if absent.
    new_experimental = list(original_experimental)
    if "ng" not in new_experimental:
        new_experimental.append("ng")

    # Reinitialise the context with "ng" injected via argparse_args so that
    # os.environ is left untouched.
    context.__init__(argparse_args=Namespace(experimental=new_experimental))

    try:
        yield
    finally:
        # Restore the context to its original state.
        context.__init__(argparse_args=Namespace(experimental=original_experimental))


def main() -> int:
    """Shim entry point: inject the ng flag and delegate to conda.cli.main."""
    from conda.cli.main import main as _main

    with _inject_ng_experimental():
        return _main()


if __name__ == "__main__":
    sys.exit(main())
