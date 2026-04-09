# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Verify that importing conda.common.serialize.yaml does not eagerly load ruamel.yaml."""

from __future__ import annotations

import subprocess
import sys
import textwrap


def test_yaml_module_does_not_eagerly_import_ruamel() -> None:
    """ruamel.yaml should only load when _yaml() is first called."""
    snippet = textwrap.dedent("""\
        import sys
        import conda.common.serialize.yaml
        print("ruamel.yaml" in sys.modules)
    """)
    result = subprocess.run(
        [sys.executable, "-c", snippet],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"Probe failed: {result.stderr}"
    assert result.stdout.strip() == "False", (
        "ruamel.yaml was loaded at import time; it should be deferred to _yaml()"
    )


def test_yaml_roundtrip_still_works() -> None:
    """Lazy loading should not break read/write functionality."""
    snippet = textwrap.dedent("""\
        from conda.common.serialize.yaml import dumps, loads
        data = {"key": "value", "nested": [1, 2, 3]}
        text = dumps(data)
        assert "key" in text
        loaded = loads(text)
        assert loaded["key"] == "value"
        assert loaded["nested"] == [1, 2, 3]
        print("ok")
    """)
    result = subprocess.run(
        [sys.executable, "-c", snippet],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"Probe failed: {result.stderr}"
    assert result.stdout.strip() == "ok"


def test_yaml_error_accessible() -> None:
    """YAMLError should be accessible as a lazy module attribute."""
    snippet = textwrap.dedent("""\
        from conda.common.serialize import yaml
        err_cls = yaml.YAMLError
        assert err_cls is not None
        print("ok")
    """)
    result = subprocess.run(
        [sys.executable, "-c", snippet],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"Probe failed: {result.stderr}"
    assert result.stdout.strip() == "ok"
