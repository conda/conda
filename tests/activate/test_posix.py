# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from shutil import which

import pytest

from conda.common.compat import on_mac, on_win


@pytest.mark.skipif(on_mac, reason="ash is not available on macOS")
@pytest.mark.skipif(on_win, reason="ash is not available on Windows")
def test_ash_available():
    assert which("ash")


def test_bash_available():
    assert which("bash")


@pytest.mark.skipif(on_win, reason="dash is not available on Windows")
def test_dash_available():
    assert which("dash")


@pytest.mark.skipif(on_win, reason="zsh is not available on Windows")
def test_zsh_available():
    assert which("zsh")
