# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Verify ``conda.plugins.types`` loads lazily and its deprecated re-exports."""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import warnings

import pytest

_DEPRECATED_NAMES = (
    "CondaAuthHandler",
    "CondaEnvironmentSpecifier",
    "CondaHealthCheck",
    "CondaPostCommand",
    "CondaPostSolve",
    "CondaPostTransactionAction",
    "CondaPreCommand",
    "CondaPrefixDataLoader",
    "CondaPreSolve",
    "CondaPreTransactionAction",
    "CondaReporterBackend",
    "CondaRequestHeader",
    "CondaSetting",
    "CondaSolver",
    "CondaSubcommand",
    "CondaVirtualPackage",
)


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


@pytest.mark.parametrize("name", _DEPRECATED_NAMES)
def test_deprecated_plugin_type_access_warns(name: str) -> None:
    """Each re-export on ``conda.plugins`` still warns and resolves to the type."""
    import conda.plugins
    import conda.plugins.types as types_mod

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        value = getattr(conda.plugins, name)

    assert any(
        issubclass(w.category, (DeprecationWarning, PendingDeprecationWarning))
        for w in caught
    ), f"expected a (Pending)DeprecationWarning for conda.plugins.{name}"
    assert value is getattr(types_mod, name)


def test_unknown_attribute_raises() -> None:
    """Unknown attributes still raise ``AttributeError``."""
    import conda.plugins

    with pytest.raises(AttributeError):
        conda.plugins.does_not_exist
