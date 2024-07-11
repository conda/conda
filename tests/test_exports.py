# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from contextlib import nullcontext

import pytest

from conda import exports
from conda.common.compat import on_win


@pytest.mark.parametrize(
    "function,raises",
    [
        ("IndexRecord", TypeError),
        ("iteritems", TypeError),
        ("Completer", None),
        ("InstalledPackages", None),
        ("hash_file", TypeError),
        ("verify", TypeError),
        ("fetch_index", TypeError),
        ("symlink_conda", TypeError),
        ("_symlink_conda_hlp", TypeError),
        pytest.param(
            "win_conda_bat_redirect",
            TypeError,
            marks=pytest.mark.skipif(
                not on_win, reason="win_conda_bat_redirect is only defined on Windows"
            ),
        ),
        ("KEYS", TypeError),
        ("KEYS_DIR", TypeError),
    ],
)
def test_deprecations(function: str, raises: type[Exception] | None) -> None:
    raises_context = pytest.raises(raises) if raises else nullcontext()
    with pytest.deprecated_call(), raises_context:
        getattr(exports, function)()
