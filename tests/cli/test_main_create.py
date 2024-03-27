# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from conda.testing import CondaCLIFixture, PathFactoryFixture


def test_environment_create_isolate_python_env(
    conda_cli: CondaCLIFixture, path_factory: PathFactoryFixture
):
    """
    Ensures that the ``pyvenv.cfg`` file is present in the environment after we create it.
    """
    prefix = path_factory()

    conda_cli(
        "create",
        f"--prefix={prefix}",
        "--isolate-python-env",
        "--yes",
    )

    pyvenv_config = prefix / "pyvenv.cfg"

    assert pyvenv_config.exists()
