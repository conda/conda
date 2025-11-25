# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import importlib

import pytest


@pytest.mark.parametrize(
    "module",
    [
        "conda_env",
        "conda_env.cli",
        "conda_env.installers",
    ],
)
def test_deprecations(module: str) -> None:
    with pytest.deprecated_call():
        importlib.import_module(module)
