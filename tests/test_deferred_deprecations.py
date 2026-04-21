# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Cold-path tests for canonicalized deprecation shims in
``conda.auxlib.logz`` and ``conda.common.serialize``.

Each case asserts that importing a module does NOT transitively import the
heavy dependency that its deprecated symbols reference. Runs in a subprocess
so the check is immune to test-order bleed-through.
"""

from __future__ import annotations

import importlib
import os
import subprocess
import sys
import textwrap
import warnings

import pytest

_CLEAN_ENV = {k: v for k, v in os.environ.items() if k != "EAGER_IMPORT"}


def _sys_modules_after(import_stmt: str) -> set[str]:
    script = textwrap.dedent(f"""
        import sys
        {import_stmt}

        for name in sorted(sys.modules):
            print(name)
    """)
    result = subprocess.run(
        [sys.executable, "-c", script],
        env=_CLEAN_ENV,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"subprocess check failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    return set(result.stdout.splitlines())


def test_auxlib_logz_does_not_pull_in_serialize_json() -> None:
    """conda.auxlib.logz must not import conda.common.serialize.json eagerly."""
    loaded = _sys_modules_after("import conda.auxlib.logz  # noqa: F401")
    assert "conda.common.serialize.json" not in loaded


def test_common_serialize_does_not_pull_in_json() -> None:
    """Importing conda.common.serialize must not import .json eagerly."""
    loaded = _sys_modules_after("import conda.common.serialize  # noqa: F401")
    assert "conda.common.serialize.json" not in loaded


@pytest.mark.parametrize(
    "module, name",
    [
        ("conda.auxlib.logz", "DumpEncoder"),
        ("conda.auxlib.logz", "_DUMPS"),
        ("conda.auxlib.logz", "jsondumps"),
        ("conda.common.serialize", "EntityEncoder"),
        ("conda.common.serialize", "json_load"),
    ],
)
def test_deprecated_symbol_access_warns(module: str, name: str) -> None:
    """Accessing a canonicalized deprecated symbol still emits a warning."""
    mod = importlib.import_module(module)
    with pytest.deprecated_call():
        getattr(mod, name)


@pytest.mark.parametrize(
    "module, name",
    [
        ("conda.auxlib.logz", "DumpEncoder"),
        ("conda.auxlib.logz", "_DUMPS"),
        ("conda.auxlib.logz", "jsondumps"),
        ("conda.common.serialize", "EntityEncoder"),
        ("conda.common.serialize", "json_load"),
    ],
)
def test_deprecated_symbol_identity_is_stable(module: str, name: str) -> None:
    """Repeated access returns the same object (factory cached)."""
    mod = importlib.import_module(module)
    with pytest.deprecated_call():
        first = getattr(mod, name)
        second = getattr(mod, name)

    assert first is second
