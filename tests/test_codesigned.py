# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from shutil import which
from subprocess import CalledProcessError, check_output, run

import pytest

from conda.common.compat import on_win

HERE = os.path.abspath(os.path.dirname(__file__))
REPO_ROOT = (Path(HERE) / "..").resolve().absolute()
STUB_FOLDER = REPO_ROOT / "conda" / "shell"


@lru_cache(maxsize=None)
def find_signtool() -> str | None:
    """Tries to find signtool

    Prefers signtool on PATH otherwise searches system.
    Ref:
      - https://learn.microsoft.com/en-us/dotnet/framework/tools/signtool-exe
      - https://learn.microsoft.com/en-us/windows/win32/seccrypto/signtool
      - https://learn.microsoft.com/en-us/windows/win32/seccrypto/using-signtool-to-verify-a-file-signature
    """
    signtool_path = which("signtool")
    if signtool_path:
        return signtool_path

    # Common installation directories where signtool might be located
    common_paths = [
        "C:\\Program Files (x86)\\Windows Kits\\10\\bin",
        "C:\\Program Files\\Windows Kits\\10\\bin",
        "C:\\Windows\\System32",
    ]

    signtool_path = None
    # Search for signtool in common paths
    for path in common_paths:
        if signtool_path:
            # We found one already
            return signtool_path
        if not os.path.exists(path):
            continue
        signtool_path = os.path.join(path, "signtool.exe")
        if os.path.exists(signtool_path):
            return signtool_path
        elif "Windows Kits" in path:
            signtool_path = None
            max_version = 0
            for dirname in os.listdir(path):
                # Use most recent signtool version
                if not dirname.endswith(".0"):
                    continue  # next dirname
                if int(dirname.replace(".", "")) < max_version:
                    continue  # next dirname

                maybe_signtool_path = os.path.join(path, dirname, "x64", "signtool.exe")
                if os.path.exists(maybe_signtool_path):
                    signtool_path = maybe_signtool_path
    return signtool_path


@lru_cache(maxsize=None)
def signtool_unsupported_because() -> str:
    reason = ""
    if not on_win:
        reason = "Only verifying signatures of stub exe's on windows"
        return reason
    signtool = find_signtool()
    if not signtool:
        reason = "signtool: unable to locate signtool.exe"
    try:
        check_output([signtool, "verify", "/?"])
    except CalledProcessError as exc:
        reason = f"signtool: something went wrong while running 'signtool verify /?', output:\n{exc.output}\n"
    return reason


def signtool_unsupported() -> bool:
    return bool(signtool_unsupported_because())


@pytest.mark.skipif(signtool_unsupported(), reason=signtool_unsupported_because())
@pytest.mark.parametrize("stub_file_name", ["cli-32.exe", "cli-64.exe"])
def test_stub_exe_signatures(stub_file_name: str) -> None:
    """Verify that signtool verifies the signature of the stub exes"""
    stub_file = STUB_FOLDER / stub_file_name
    signtool_exe = find_signtool()
    completed_process = run([signtool_exe, "verify", "/pa", "/v", stub_file])
    assert completed_process.returncode == 0
