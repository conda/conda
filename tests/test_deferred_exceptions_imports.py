# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Verify that importing conda.exceptions does not eagerly load heavy deps.

These imports are only needed when formatting specific error messages,
not when defining exception classes.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap

import pytest


@pytest.mark.parametrize(
    "module",
    [
        "conda.models.channel",
        "conda.auxlib.logz",
        "conda.common.iterators",
    ],
)
def test_exceptions_does_not_eagerly_import(module: str) -> None:
    """Heavy deps should be deferred to error-path methods."""
    snippet = textwrap.dedent(f"""\
        import sys
        import conda.exceptions
        print("{module}" in sys.modules)
    """)
    result = subprocess.run(
        [sys.executable, "-c", snippet],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"Probe failed: {result.stderr}"
    assert result.stdout.strip() == "False", (
        f"{module} was loaded at import time; it should be deferred"
    )
