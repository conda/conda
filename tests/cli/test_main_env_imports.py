# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Verify that importing conda.cli.main_env does not eagerly load main_export."""

from __future__ import annotations

import subprocess
import sys
import textwrap


def test_main_env_does_not_eagerly_import_main_export() -> None:
    """main_env should defer main_export until configure_parser() is called."""
    snippet = textwrap.dedent("""\
        import sys
        import conda.cli.main_env
        print("conda.cli.main_export" in sys.modules)
    """)
    result = subprocess.run(
        [sys.executable, "-c", snippet],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"Probe failed: {result.stderr}"
    assert result.stdout.strip() == "False", (
        "main_export was loaded at import time; it should be deferred to configure_parser()"
    )
