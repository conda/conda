# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Verify the extraction worker module stays import-light."""

from __future__ import annotations

import subprocess
import sys


def test_extract_module_does_not_import_runtime_state() -> None:
    script = """\
import sys
import conda._private.extract

for name in sorted(sys.modules):
    print(name)
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    imported = set(result.stdout.splitlines())
    conda_modules = {
        name for name in imported if name == "conda" or name.startswith("conda.")
    }
    assert conda_modules <= {
        "conda",
        "conda._private",
        "conda._private.extract",
        "conda._version",
    }
    assert not any(name.startswith("conda_package_handling") for name in imported)
