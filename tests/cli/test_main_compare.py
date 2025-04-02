# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING
from unittest import mock

import pytest

from conda.base.context import context
from conda.exceptions import EnvironmentLocationNotFound

if TYPE_CHECKING:
    from pathlib import Path

    from conda.testing.fixtures import CondaCLIFixture


def test_compare(tmp_path: Path, conda_cli: CondaCLIFixture):
    mocked = mock.patch.object(
        context,
        "envs_dirs",
        return_value=(str(tmp_path),),
    )

    with pytest.raises(EnvironmentLocationNotFound):
        conda_cli("compare", "--name", "nonexistent", "tempfile.rc", "--json")

    assert mocked.call_count > 0
