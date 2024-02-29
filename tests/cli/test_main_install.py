# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from conda.testing import CondaCLIFixture, TmpEnvFixture


def test_environment_install_no_python_user_site_packages(
    conda_cli: CondaCLIFixture,
    tmp_env: TmpEnvFixture,
):
    """
    Ensures that the ``pyvenv.cfg`` file is present in the environment after we create it.
    """
    with tmp_env() as prefix:
        pyvenv_config = prefix / "pyvenv.cfg"
        assert not pyvenv_config.exists()

        conda_cli(
            "install",
            f"--prefix={prefix}",
            "--no-python-user-site-packages",
            "--yes",
            "python",
        )

        assert pyvenv_config.exists()
