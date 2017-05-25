# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from conda.common.compat import on_win
from conda.common.platform import is_admin_on_windows


def test_is_admin_on_windows():
    result = is_admin_on_windows()
    if not on_win:
        assert result is False
    else:
        assert result is False or result is True
