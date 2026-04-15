# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from conda.common.compat import on_win
from conda.models.match_spec import MatchSpec
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


def test_specs_by_name_copy_is_independent() -> None:
    """Copying specs_by_name with a dict comprehension must yield independent lists."""
    seed = {
        "numpy": [MatchSpec("numpy>=1.20")],
        "scipy": [MatchSpec("scipy")],
    }
    copy = {k: list(v) for k, v in seed.items()}

    copy["numpy"].append(MatchSpec("numpy<2"))
    assert len(seed["numpy"]) == 1, "seed must not be mutated by changes to the copy"
    assert len(copy["numpy"]) == 2
