# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Verify ``conda.plugins.types`` loads lazily and its deprecated re-exports."""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap

import pytest


def test_plugins_types_not_imported_on_plugins_import() -> None:
    """Importing ``conda.plugins`` must not eagerly import ``conda.plugins.types``."""
    script = textwrap.dedent("""
        import sys
        import conda.plugins
        print("conda.plugins.types" in sys.modules)
    """)
    env = {k: v for k, v in os.environ.items() if k != "EAGER_IMPORT"}
    result = subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False", result.stdout


def test_plugins_types_requires_explicit_import() -> None:
    """``conda.plugins.types`` is available only after explicit import."""
    script = textwrap.dedent("""
        import conda.plugins

        try:
            conda.plugins.types
        except AttributeError:
            print("missing")
        else:
            raise SystemExit("conda.plugins.types should require explicit import")

        import conda.plugins.types
        print(conda.plugins.types.__name__)
    """)
    env = {k: v for k, v in os.environ.items() if k != "EAGER_IMPORT"}
    result = subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["missing", "conda.plugins.types"]


def test_unknown_attribute_raises() -> None:
    """Unknown attributes still raise ``AttributeError``."""
    import conda.plugins

    with pytest.raises(AttributeError):
        conda.plugins.does_not_exist
