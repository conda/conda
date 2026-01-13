# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda.common.compat import on_win

from . import Shell

if TYPE_CHECKING:
    from collections.abc import Iterator

    from pytest import FixtureRequest

    from conda.testing.fixtures import TmpEnvFixture


@pytest.fixture(scope="module")
def shell(request: FixtureRequest) -> Shell:
    try:
        shell = request.param
    except AttributeError:
        # AttributeError: 'FixtureRequest' object has no attribute 'param'
        shell = "cmd.exe" if on_win else "bash"
    return Shell.resolve(shell)


@pytest.fixture
def shell_wrapper_integration(
    tmp_env: TmpEnvFixture,
) -> Iterator[tuple[str, str, str]]:
    with (
        tmp_env() as prefix,
        tmp_env(prefix=prefix / "envs" / "charizard") as prefix2,
        tmp_env(prefix=prefix / "envs" / "venusaur") as prefix3,
    ):
        yield str(prefix), str(prefix2), str(prefix3)
