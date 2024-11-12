# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from conda.testing.fixtures import TmpEnvFixture


@pytest.mark.integration
def test_link_order_post_link_actions(
    test_recipes_channel: Path, tmp_env: TmpEnvFixture
):
    with tmp_env("c_post_link_package"):
        pass


@pytest.mark.integration
def test_link_order_post_link_depend(
    test_recipes_channel: Path, tmp_env: TmpEnvFixture
):
    with tmp_env("e_post_link_package"):
        pass
