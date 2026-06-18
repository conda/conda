# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda.common.compat import on_win
from conda.exceptions import UnsatisfiableError
from conda.models.match_spec import MatchSpec
from conda.resolve import Resolve
from conda.testing import helpers

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


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

    assert copy["numpy"] is not seed["numpy"], "values must be distinct list objects"
    copy["numpy"].append(MatchSpec("numpy<2"))
    assert len(seed["numpy"]) == 1, "seed must not be mutated by changes to the copy"
    assert len(copy["numpy"]) == 2


def test_solve_wrong_version_calls_find_conflicts(
    mocker: MockerFixture,
) -> None:
    """Wrong-version specs route through find_conflicts without crashing.

    build_conflict_map cannot derive chains when no package matches the spec,
    so bad_deps has the classified shape but empty category sets.
    """
    rec = helpers.record(name="foo", version="1.0")
    resolve = Resolve({rec: rec})
    spec = MatchSpec("foo=99.0")

    mocker.patch("conda.resolve.Resolve.get_reduced_index", return_value={})
    find_conflicts = mocker.spy(resolve, "find_conflicts")
    unsatisfiable_init = mocker.spy(UnsatisfiableError, "__init__")

    with pytest.raises(UnsatisfiableError):
        resolve.solve([spec])

    find_conflicts.assert_called_once_with({spec}, None, None)
    bad_deps = unsatisfiable_init.call_args.args[1]
    assert bad_deps == {
        "python": set(),
        "request_conflict_with_history": set(),
        "direct": set(),
        "virtual_package": set(),
    }
