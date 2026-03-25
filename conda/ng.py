# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
conda-ng entry point, to be used as `python -m conda.ng`.
"""

if __name__ == "__main__":
    import os

    from .cli import main

    os.environ["CONDA_EXPERIMENTAL"] = ",".join(
        dict.fromkeys(["ng", *os.environ.get("CONDA_EXPERIMENTAL", "").split(",")])
    )
    main()
