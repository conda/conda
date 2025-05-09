# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

from contextlib import nullcontext

import pytest

with pytest.deprecated_call():
    from conda.env.specs import binstar


@pytest.mark.parametrize(
    "function,raises",
    [
        ("ENVIRONMENT_TYPE", TypeError),
        ("BinstarSpec", None),
    ],
)
def test_deprecations(function: str, raises: type[Exception] | None) -> None:
    raises_context = pytest.raises(raises) if raises else nullcontext()
    with pytest.deprecated_call(), raises_context:
        getattr(binstar, function)()


def test_cannot_handle_file_path():
    spec = binstar.BinstarSpec("/file/path/doesnt/exist")
    assert spec.valid_name() is False


def test_can_handle_binstar_name():
    spec = binstar.BinstarSpec("conda-test/test")
    assert spec.valid_name()

    spec = binstar.BinstarSpec("user-name/Package_Name")
    assert spec.valid_name()

    spec = binstar.BinstarSpec("user.123/My Package 1.0")
    assert spec.valid_name()
