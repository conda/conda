# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest

import conda.plugins.hookspec


@pytest.mark.parametrize(
    "constant",
    ["spec_name"],
)
def test_deprecations(constant: str) -> None:
    with pytest.deprecated_call():
        getattr(conda.plugins.hookspec, constant)
