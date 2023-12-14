# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from os.path import (
    exists,
    join,
)

from conda.gateways.disk.delete import path_is_clean
from conda.testing import CondaCLIFixture, TmpEnvFixture
from conda.testing.integration import (
    PYTHON_BINARY,
    package_is_installed,
)


def test_remove_all_keep_env(tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture):
    with tmp_env("python") as prefix:
        assert exists(join(prefix, PYTHON_BINARY))
        assert package_is_installed(prefix, "python")

        conda_cli("remove", f"--prefix={prefix}", "--all", "--keep-env", "--yes")
        assert not path_is_clean(prefix)
