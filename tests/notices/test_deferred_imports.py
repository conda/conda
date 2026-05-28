# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Verify that importing conda.notices.core does not eagerly load heavy deps.

These tests run in a subprocess to get a clean sys.modules snapshot,
ensuring the deferred imports in notices/core.py are actually deferred.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap

import pytest


@pytest.mark.parametrize(
    "module",
    [
        "conda.notices.fetch",
        "conda.notices.cache",
        "conda.notices.views",
        "conda.notices.types",
        "conda.models.channel",
    ],
)
def test_notices_core_does_not_eagerly_import(module: str) -> None:
    """Importing notices.core should not pull in fetch, cache, views, or models."""
    snippet = textwrap.dedent(f"""\
        import sys
        from conda.notices.core import notices, retrieve_notices, display_notices
        present = "{module}" in sys.modules
        print(present)
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


def test_notices_core_does_not_load_requests() -> None:
    """The @notices decorator should be importable without pulling in requests."""
    snippet = textwrap.dedent("""\
        import sys
        from conda.notices.core import notices
        print("requests" in sys.modules)
    """)
    result = subprocess.run(
        [sys.executable, "-c", snippet],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"Probe failed: {result.stderr}"
    assert result.stdout.strip() == "False", (
        "requests was loaded by importing notices.core; it should be deferred"
    )
