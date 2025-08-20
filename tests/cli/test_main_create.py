# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda.base.context import reset_context
from conda.exceptions import CondaValueError

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import MonkeyPatch

    from conda.testing.fixtures import CondaCLIFixture


def test_create_default_packages_can_not_be_explicit(
    monkeypatch: MonkeyPatch,
    conda_cli: CondaCLIFixture,
    tmp_path: Path,
):
    monkeypatch.setenv(
        "CONDA_CREATE_DEFAULT_PACKAGES",
        "https://repo.anaconda.com/pkgs/main/linux-64/ca-certificates-2025.2.25-h06a4308_0.conda",
    )
    reset_context()
    with pytest.raises(CondaValueError) as err:
        conda_cli("create", "--prefix", tmp_path, "--yes")
    assert (
        "Conda setting `create_default_packages` must not include references to explicit packages."
        in err.value.message
    )
