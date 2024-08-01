# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from shutil import which

import pytest

from conda.common.compat import on_mac, on_win

pytestmark = [
    pytest.mark.skipif(on_mac, reason="ash is not available on macOS"),
    pytest.mark.skipif(on_win, reason="ash is not available on Windows"),
]


def test_ash_available():
    assert which("ash")
