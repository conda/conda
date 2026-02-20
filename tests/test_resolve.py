# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from conda.common.compat import on_win
from conda.resolve import Resolve


def test_Resolve_make_channel_priorities():
    channels = ["conda-canary", "defaults", "conda-forge"]
    names = (
        "conda-canary",
        "pkgs/main",
        "pkgs/r",
        *(["pkgs/msys2"] if on_win else []),
        "conda-forge",
    )
    assert Resolve._make_channel_priorities(channels) == {
        name: weight for weight, name in enumerate(names)
    }
