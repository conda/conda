# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from conda.resolve import Resolve


def test_Resolve_make_channel_priorities():
    channels = ["conda-canary", "defaults", "conda-forge"]
    assert Resolve._make_channel_priorities(channels) == {
        "conda-canary": 0,
        "pkgs/main": 1,
        "pkgs/r": 2,
        "conda-forge": 3,
    }
