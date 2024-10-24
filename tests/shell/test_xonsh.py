# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import pytest

from . import SKIPIF_ON_WIN

pytestmark = [
    pytest.mark.integration,
    # skip on Windows since it's harder to install correctly
    SKIPIF_ON_WIN,
]
PARAMETRIZE_XONSH = pytest.mark.parametrize("shell", ["xonsh"], indirect=True)


@PARAMETRIZE_XONSH
def test_shell_available(shell: str) -> None:
    # the fixture does all the work
    pass
