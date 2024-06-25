# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from contextlib import nullcontext

import pytest

from conda import exports
from conda.common.compat import on_win


@pytest.mark.parametrize(
    "function,deprecated,raises",
    [
        ("IndexRecord", True, TypeError),
        ("iteritems", True, TypeError),
        ("InstalledPackages", True, None),
        ("hash_file", True, TypeError),
        ("fetch_index", True, TypeError),
        ("symlink_conda", True, TypeError),
        ("_symlink_conda_hlp", True, TypeError),
        pytest.param(
            "win_conda_bat_redirect",
            True,
            TypeError,
            marks=pytest.mark.skipif(
                not on_win,
                reason="win_conda_bat_redirect is on Windows only",
            ),
        ),
    ],
)
def test_deprecations(
    function: str,
    deprecated: bool,
    raises: type[Exception] | None,
) -> None:
    deprecated_context = pytest.deprecated_call() if deprecated else nullcontext()
    raises_context = pytest.raises(raises) if raises else nullcontext()
    with deprecated_context, raises_context:
        getattr(exports, function)()
