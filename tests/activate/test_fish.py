# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from shutil import which

import pytest

from conda.common.compat import on_win

pytestmark = pytest.mark.skipif(on_win, reason="fish is not available on Windows")


def test_fish_available():
    assert which("fish")
