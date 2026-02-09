# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from importlib import import_module, reload

import pytest


@pytest.mark.parametrize(
    "module",
    ["conda.trust", "conda.trust.constants", "conda.trust.signature_verification"],
)
def test_deprecations(module: str) -> None:
    with pytest.deprecated_call():
        reload(import_module(module))
