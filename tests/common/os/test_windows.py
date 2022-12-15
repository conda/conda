# SPDX-FileCopyrightText: © 2012 Continuum Analytics, Inc. <http://continuum.io>
# SPDX-FileCopyrightText: © 2017 Anaconda, Inc. <https://www.anaconda.com>
# SPDX-License-Identifier: BSD-3-Clause
from conda.common.compat import on_win
from conda.common._os.windows import is_admin_on_windows


def test_is_admin_on_windows():
    result = is_admin_on_windows()
    if on_win:
        assert result is False or result is True
    else:
        assert result is False
