# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from shutil import which

import pytest

from conda.common.compat import on_win


@pytest.mark.skipif(on_win, reason="csh is not available on Windows")
def test_csh_available():
    assert which("csh")


@pytest.mark.skipif(on_win, reason="tcsh is not available on Windows")
def test_tcsh_available():
    assert which("tcsh")
