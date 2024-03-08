# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from shutil import which

import pytest

from conda.common.compat import on_linux, on_mac

pytestmark = [
    pytest.mark.skipif(on_linux, reason="cmd.exe is not available on Linux"),
    pytest.mark.skipif(on_mac, reason="cmd.exe is not available on macOS"),
]


def test_cmd_exe_available():
    assert which("cmd.exe")
