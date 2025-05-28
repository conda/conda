# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from conda.common._os.windows import is_admin_on_windows
from conda.common.compat import on_win


def test_is_admin_on_windows():
    result = is_admin_on_windows()
    if on_win:
        assert result is False or result is True
    else:
        assert result is False
