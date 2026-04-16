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


def test_plugins_types_attribute_loads_lazily_without_warning() -> None:
    """``conda.plugins.types`` attribute access loads the submodule, no warning."""
    import conda.plugins

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        types_module = conda.plugins.types

    assert types_module is sys.modules["conda.plugins.types"]
    assert not any(
        issubclass(w.category, (DeprecationWarning, PendingDeprecationWarning))
        for w in caught
    ), [str(w.message) for w in caught]


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
