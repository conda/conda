# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

from contextlib import nullcontext

import pytest

from conda.env.specs import binstar


@pytest.mark.parametrize(
    "function,raises",
    [
        ("ENVIRONMENT_TYPE", TypeError),
    ],
)
def test_deprecations(function: str, raises: type[Exception] | None) -> None:
    raises_context = pytest.raises(raises) if raises else nullcontext()
    with pytest.deprecated_call(), raises_context:
        getattr(binstar, function)()
