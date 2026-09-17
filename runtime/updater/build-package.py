# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Set the release version in rattler-build's source copy and install it."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    version = os.environ["CONDA_RUNTIME_VERSION"]
    manifest = Path("pyproject.toml")
    contents = manifest.read_text(encoding="utf-8")
    development_version = 'version = "0.1.0"'
    if contents.count(development_version) != 1:
        raise SystemExit("updater metadata must contain one development version")
    manifest.write_text(
        contents.replace(development_version, f'version = "{version}"'),
        encoding="utf-8",
    )
    subprocess.run(
        [sys.executable, "-m", "pip", "install", ".", "-vv", "--no-deps", "--no-build-isolation"],
        check=True,
    )


if __name__ == "__main__":
    main()
