# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
conda-ng entry point, to be used as `python -m conda.ng`.
"""

if __name__ == "__main__":
    from ._ng.cli import main

    main()
