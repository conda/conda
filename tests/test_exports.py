# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from contextlib import nullcontext

import pytest

from conda import exports


@pytest.mark.parametrize(
    "function,raises",
    [
        ("EntityEncoder", None),
        ("input", OSError),
        ("StringIO", None),
        ("PY3", TypeError),
        ("string_types", None),
        ("text_type", None),
        ("DEFAULT_CHANNELS", TypeError),
        ("DEFAULT_CHANNELS_UNIX", TypeError),
        ("DEFAULT_CHANNELS_WIN", TypeError),
        ("PREFIX_PLACEHOLDER", TypeError),
        ("_PREFIX_PLACEHOLDER", TypeError),
        ("prefix_placeholder", TypeError),
        ("CondaError", TypeError),
        ("CondaHTTPError", TypeError),
        ("CondaOSError", TypeError),
        ("LinkError", TypeError),
        ("LockError", TypeError),
        ("PaddingError", TypeError),
        ("PathNotFoundError", TypeError),
        ("CondaFileNotFoundError", TypeError),
        ("UnsatisfiableError", TypeError),
    ],
)
def test_deprecations(function: str, raises: type[Exception] | None) -> None:
    raises_context = pytest.raises(raises) if raises else nullcontext()
    with pytest.deprecated_call(), raises_context:
        getattr(exports, function)()
