# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause


from conda.cli.conda_argparse import BUILTIN_COMMANDS
from conda.testing import CondaCLIFixture


def test_commands(conda_cli: CondaCLIFixture):
    stdout, stderr, code = conda_cli("commands")

    assert stdout == "\n".join(
        sorted(
            {
                *BUILTIN_COMMANDS,
                "content-trust",  # from conda-content-trust
                "doctor",  # builtin plugin
                "repoquery",  # from conda-libmamba-solver
                "server",  # from anaconda-client
            }
        )
    )
    assert not stderr
    assert not code
