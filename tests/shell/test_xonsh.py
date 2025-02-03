# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import pytest

from conda.common.compat import on_win

pytestmark = [
    pytest.mark.integration,
    # skip on Windows since it's harder to install correctly
    pytest.mark.skipif(on_win, reason="unavailable on Windows"),
]
PARAMETRIZE_XONSH = pytest.mark.parametrize("shell", ["xonsh"], indirect=True)


@PARAMETRIZE_XONSH
def test_shell_available(shell: str) -> None:
    # the `shell` fixture does all the work
    pass
