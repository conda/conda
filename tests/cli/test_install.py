# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from contextlib import nullcontext

import pytest

from conda.base.context import context
from conda.cli.install import Repodatas
from conda.exceptions import PackagesNotFoundError, ResolvePackageNotFound
from conda.models.match_spec import MatchSpec


class TestException(Exception):
    pass


TEST_SPEC = "spec==0.0"
TEST_REPODATA1 = "1.json"
TEST_REPODATA2 = "2.json"
TEST_REPODATA3 = "3.json"
TEST_REPODATAS = [TEST_REPODATA1, TEST_REPODATA2, TEST_REPODATA3]
TEST_INDEX_ARGS = {
    "channel_urls": (),
    "prepend": True,
    "use_local": False,
}


@pytest.mark.parametrize(
    "successes,raises,expected",
    [
        pytest.param(
            [True, True, True],
            False,
            TEST_REPODATA1,
            id="pass1,pass2,pass3 -> pass1",
        ),
        pytest.param(
            [False, True, True],
            False,
            TEST_REPODATA2,
            id="fail1,pass2,pass3 -> pass2",
        ),
        pytest.param(
            [False, False, True],
            False,
            TEST_REPODATA3,
            id="fail1,fail2,pass3 -> pass3",
        ),
        pytest.param(
            [False, False, False],
            True,
            TEST_REPODATA3,
            id="fail1,fail2,fail3 -> fail3",
        ),
        pytest.param(
            [False, True, False],
            False,
            TEST_REPODATA2,
            id="fail1,pass2,fail3 -> pass2",
        ),
    ],
)
def test_Repodatas_TestException(successes: list[bool], raises: bool, expected: str):
    repodatas = Repodatas(TEST_REPODATAS, TEST_INDEX_ARGS, [TestException])
    with pytest.raises(TestException, match=expected) if raises else nullcontext():
        for repodata_manager, repodata_success in zip(repodatas, successes):
            with repodata_manager as repodata:
                if not repodata_success:
                    raise TestException(repodata)

        # final assertion only occurs on success
        assert repodata == expected


@pytest.mark.parametrize(
    "exception",
    [
        ResolvePackageNotFound([[MatchSpec(TEST_SPEC)]]),
        PackagesNotFoundError([MatchSpec(TEST_SPEC)], context.channels),
    ],
)
def test_Repodatas_special_exceptions(exception: Exception):
    repodatas = Repodatas(TEST_REPODATAS, TEST_INDEX_ARGS)
    with pytest.raises(PackagesNotFoundError, match=TEST_SPEC):
        for repodata_manager in repodatas:
            with repodata_manager:
                raise exception
