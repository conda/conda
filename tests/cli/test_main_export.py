# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from conda.exceptions import CondaValueError


def test_export_invalid_platform_fails_fast(conda_cli):
    with pytest.raises(CondaValueError, match="Could not find platform"):
        conda_cli(
            "export",
            "--override-platforms",
            "--platform",
            "idontexist",
        )
