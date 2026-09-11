# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Check the native Windows ARM64 test environment from the repository root."""

from __future__ import annotations

import platform
import subprocess
import sys
import sysconfig
from pathlib import Path

import libmambapy

import conda
from conda.base.context import context
from conda.core.launchers import get_windows_launcher_stub
from conda.core.prefix_data import PrefixData
from conda.gateways.disk.read import compute_sum

subprocess.run(["git", "--version"], check=True)
subprocess.run(["minio", "--version"], check=True)

assert sys.version_info[:2] == (3, 14), sys.version
assert platform.machine().lower() == "arm64", platform.machine()
assert sysconfig.get_platform() == "win-arm64", sysconfig.get_platform()
assert context.subdir == "win-arm64", context.subdir
assert context.solver == "libmamba", context.solver
assert Path(conda.__file__).samefile(Path("conda/__init__.py"))
assert PrefixData(sys.prefix).get("python").subdir == "win-arm64"
records = tuple(PrefixData(sys.prefix).iter_records())
assert {record.subdir for record in records} <= {"noarch", "win-arm64"}
launcher, sha256 = get_windows_launcher_stub(sys.prefix, source_prefixes=(sys.prefix,))
assert Path(launcher).name == "cli-arm64.exe", launcher
assert compute_sum(Path(sys.prefix) / "Scripts/conda.exe", "sha256") == sha256
print(f"Python: {sys.executable} ({platform.machine()})")
print(f"Conda: {conda.__file__} ({context.subdir}, {context.solver})")
print(f"libmambapy: {libmambapy.__file__}")
print(f"Launcher: {launcher}")
