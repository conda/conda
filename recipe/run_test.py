# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Check that released Windows ARM64 conda can upgrade to the built package."""

# conda-build automatically runs this extra upgrade check for canary builds.
# ruff: noqa: S101

import os
import struct
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from conda.base.context import context
from conda.core.prefix_data import PrefixData


def test_windows_arm64_upgrade():
    assert context._native_subdir() == "win-arm64"
    candidate = PrefixData(sys.prefix).get("conda")
    assert candidate.sha256
    compatibility = Path(sys.prefix) / "Lib/site-packages/conda/shell/cli-arm64.exe"
    expected_launcher = compatibility.read_bytes()
    env = os.environ.copy()
    env["CONDA_REGISTER_ENVS"] = "false"
    env["CONDA_SUBDIR"] = "win-arm64"

    def run(*args):
        result = subprocess.run(args, env=env, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr or result.stdout
        return result.stdout

    with TemporaryDirectory() as directory:
        prefix = Path(directory) / "conda"
        run(
            sys.executable,
            "-I",
            "-m",
            "conda",
            "create",
            f"--prefix={prefix}",
            "--yes",
            "--override-channels",
            "-c",
            "https://repo.anaconda.com/pkgs/main",
            "conda=26.7.2=py314h46a1fef_1",
            "python=3.14",
            "pip=26.1.2=pyh0d26453_0",
        )
        records = PrefixData(prefix)
        assert records.get("conda").build == "py314h46a1fef_1"
        python = prefix / "python.exe"
        assert run(python, "-I", "-m", "conda", "--version").strip() == "conda 26.7.2"

        run(
            python,
            "-I",
            "-m",
            "conda",
            "install",
            f"--prefix={prefix}",
            "--yes",
            "--override-channels",
            "-c",
            candidate.channel.base_url,
            "-c",
            "https://repo.anaconda.com/pkgs/main",
            f"conda={candidate.version}={candidate.build}",
            "conda-launchers=24.7.1=hd3eb1b0_6",
            "pip=26.2.1=pyh0d26453_0",
        )
        records.reload()
        assert records.get("conda").sha256 == candidate.sha256
        assert records.get("pip").version == "26.2.1"
        for command in ("pip", "pip3"):
            executable = prefix / "Scripts" / f"{command}.exe"
            launcher = executable.read_bytes()
            assert launcher == expected_launcher
            pe_offset = struct.unpack_from("<I", launcher, 0x3C)[0]
            assert struct.unpack_from("<H", launcher, pe_offset + 4)[0] == 0xAA64
            assert (prefix / "Scripts" / f"{command}-script.py").is_file()
            assert run(executable, "--version").startswith("pip 26.2.1 ")


if context.subdir == "win-arm64":
    test_windows_arm64_upgrade()
