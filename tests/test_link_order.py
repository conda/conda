# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from pathlib import Path

import pytest

from conda.testing import TmpEnvFixture


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
