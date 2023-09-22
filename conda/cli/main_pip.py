# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""PEP 621 compatible entry point used when `conda init` has not updated the user shell profile."""
import os
import sys
from logging import getLogger

from .. import CondaError
from ..auxlib.ish import dals
from .main import main as main_main

log = getLogger(__name__)


def pip_installed_post_parse_hook(args, p):
    if args.cmd not in ("init", "info"):
        raise CondaError(
            dals(
                """
        Conda has not been initialized.

        To enable full conda functionality, please run 'conda init'.
        For additional information, see 'conda init --help'.

        """
            )
        )


def main(*args, **kwargs):
    os.environ["CONDA_PIP_UNINITIALIZED"] = "true"
    kwargs["post_parse_hook"] = pip_installed_post_parse_hook
    return main_main(*args, **kwargs)


if __name__ == "__main__":
    sys.exit(main())
