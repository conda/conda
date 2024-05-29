# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from conda.testing import CondaCLIFixture, TmpEnvFixture


def test_environment_update_isolate_python_env(
    conda_cli: CondaCLIFixture,
    tmp_env: TmpEnvFixture,
):
    """
    Ensures that the ``pyvenv.cfg`` file is present in the environment after we update it.
    """
    with tmp_env("python") as prefix:
        pyvenv_config = prefix / "pyvenv.cfg"
        assert not pyvenv_config.exists()

        conda_cli(
            "update",
            f"--prefix={prefix}",
            "--isolate-python-env",
            "--yes",
            "python",
        )

        assert pyvenv_config.exists()
