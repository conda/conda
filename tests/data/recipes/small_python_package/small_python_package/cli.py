# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
CLI interface for small-python-package.
"""

import argparse

from . import __version__, hello


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="A small Python package for conda testing"
    )
    parser.add_argument(
        "--version", action="version", version=f"small-python-package {__version__}"
    )
    parser.add_argument("--greet", action="store_true", help="Print a greeting")

    args = parser.parse_args()

    if args.greet:
        print(hello())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
