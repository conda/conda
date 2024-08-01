# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from shutil import which

from conda.common.compat import on_win


def test_powershell_available():
    assert which("powershell" if on_win else "pwsh")
