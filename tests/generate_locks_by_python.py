#!/usr/bin/env python3
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (C) conda contributors
# SPDX-License-Identifier: BSD-3-Clause
"""Prototype of generate_locks_by_python.sh — needs conda-lockfiles in base. Run from repo root."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYTHON_VERSIONS = ("3.10", "3.11", "3.12", "3.13")
PYTHON_LINE = re.compile(r"^(\s*-\s*)python.*$", re.MULTILINE)
PLATFORMS = ("win-64", "linux-64", "osx-arm64", "osx-64", "linux-aarch64")


def conda_exe() -> str:
    exe = os.environ.get("CONDA_EXE")
    if exe and os.access(exe, os.X_OK):
        return exe
    base = subprocess.check_output(["conda", "info", "--base"], text=True).strip()
    return f"{base}/bin/conda"


def main() -> None:
    os.chdir(ROOT)
    conda = conda_exe()
    base = subprocess.check_output([conda, "info", "--base"], text=True).strip()
    prefix = f"{base}/envs/_conda_lock_by_py"
    env_path = (
        Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "tests" / "environment.yml"
    )
    text = env_path.read_text(encoding="utf-8")

    for py in PYTHON_VERSIONS:
        patched = PYTHON_LINE.sub(rf"\1python {py}.*", text)
        out = ROOT / "tests" / f"conda-lock-python-{py}.yml"
        print(f"==> python {py} -> {out}", file=sys.stderr)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False, encoding="utf-8"
        ) as f:
            f.write(patched)
            tmp = f.name
        try:
            subprocess.run(
                [conda, "remove", "-p", prefix, "--all", "-y"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.run(
                [conda, "create", "-p", prefix, "--file", tmp, "-y"], check=True
            )
        finally:
            Path(tmp).unlink(missing_ok=True)

        cmd = [
            conda,
            "export",
            "-p",
            prefix,
            "--format",
            "conda-lock-v1",
            "--file",
            str(out),
        ]
        for plat in PLATFORMS:
            cmd.extend(["--platform", plat])
        subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
