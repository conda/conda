# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from contextlib import nullcontext

import pytest

from conda.gateways.disk import create


@pytest.mark.parametrize(
    "function,raises",
    [
        ("create_application_entry_point", TypeError),
        ("ProgressFileWrapper", TypeError),
        ("create_fake_executable_softlink", TypeError),
        ("extract_tarball", TypeError),
    ],
)
def test_deprecations(function: str, raises: type[Exception] | None) -> None:
    raises_context = pytest.raises(raises) if raises else nullcontext()
    with pytest.deprecated_call(), raises_context:
        getattr(create, function)()
