#!/usr/bin/env python3
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Exercise the host installer against staged release assets without downloading."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

TARGETS = {
    ("Linux", "x86_64"): "x86_64-unknown-linux-gnu",
    ("Linux", "aarch64"): "aarch64-unknown-linux-gnu",
    ("Darwin", "x86_64"): "x86_64-apple-darwin",
    ("Darwin", "arm64"): "aarch64-apple-darwin",
    ("Windows", "AMD64"): "x86_64-pc-windows-msvc.exe",
}


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def installer_command(root: Path, assets: Path, env: dict[str, str]) -> list[str]:
    if os.name == "nt":
        shell = shutil.which("pwsh") or shutil.which("powershell")
        if shell is None:
            raise SystemExit("PowerShell is required to test the Windows installer")
        wrapper = root / "install.ps1"
        wrapper.write_text(
            """$ErrorActionPreference = "Stop"
function Invoke-WebRequest {
    param([switch] $UseBasicParsing, [uri] $Uri, [string] $OutFile)
    $Name = [IO.Path]::GetFileName($Uri.AbsolutePath)
    Copy-Item -LiteralPath (Join-Path $env:RELEASE_ASSETS $Name) -Destination $OutFile
}
& (Join-Path $env:RELEASE_ASSETS "install.ps1") -InstallDir $env:INSTALL_DIR
if ($env:CONDA_SHIP_INTERNAL_UPDATE_INSTRUCTION -ne "preserve caller environment") {
    throw "Installer did not restore the caller environment"
}
""",
            encoding="utf-8",
        )
        return [shell, "-NoProfile", "-File", str(wrapper)]
    tools = root / "tools"
    tools.mkdir()
    curl = tools / "curl"
    curl.write_text(
        '#!/bin/sh\nset -eu\nname=${7##*/}\ncp "$RELEASE_ASSETS/$name" "$6"\n',
        encoding="utf-8",
    )
    curl.chmod(0o755)
    env["PATH"] = str(tools) + os.pathsep + env["PATH"]
    return ["sh", str(assets / "install.sh"), env["INSTALL_DIR"]]


def prove_installers(assets: Path, version: str) -> None:
    target = TARGETS.get((platform.system(), platform.machine()))
    if target is None:
        raise SystemExit("unsupported installer proof platform")
    asset = assets / f"conda-{target}"
    with tempfile.TemporaryDirectory(prefix="conda-installer-") as directory:
        root = Path(directory).resolve()
        prefix = root / "prefix"
        install_dir = root / "bin"
        destination = install_dir / ("conda.exe" if os.name == "nt" else "conda")
        env = os.environ.copy()
        env.update(
            RELEASE_ASSETS=str(assets.resolve()),
            INSTALL_DIR=str(install_dir),
            CONDA_SHIP_PREFIX=str(prefix),
            XDG_DATA_HOME=str(root / "data"),
            LOCALAPPDATA=str(root / "data"),
            CONDA_OFFLINE="1",
            CONDA_SHIP_INTERNAL_UPDATE_INSTRUCTION="preserve caller environment",
        )
        command = installer_command(root, assets.resolve(), env)
        installed = subprocess.run(command, env=env, capture_output=True, text=True)
        if installed.returncode:
            raise SystemExit(f"installer failed: {installed.stderr.strip()}")
        expected_hash = sha256(asset)
        if sha256(destination) != expected_hash:
            raise SystemExit("installed executable differs from the release asset")
        record = json.loads((prefix / ".conda.json").read_text(encoding="utf-8"))
        update = record.get("update", {})
        expected = {
            "ownership": "direct",
            "installation": "standalone",
            "package": "conda-runtime",
            "instruction": None,
        }
        if any(update.get(key) != value for key, value in expected.items()):
            raise SystemExit("installer did not record direct ownership")
        if Path(update.get("executable", "")).resolve() != destination:
            raise SystemExit("installer recorded a different executable")
        result = subprocess.run(
            [str(destination), "--version"], env=env, capture_output=True, text=True
        )
        if result.returncode or result.stdout.strip() != f"conda {version}":
            raise SystemExit(
                f"installed conda version differs: {result.stderr.strip()}"
            )
        repeated = subprocess.run(command, env=env, capture_output=True, text=True)
        if (
            repeated.returncode == 0
            or "refusing to replace" not in repeated.stderr.lower()
        ):
            raise SystemExit("installer did not refuse an existing executable")
        if sha256(destination) != expected_hash:
            raise SystemExit("refused installation changed the executable")
    print(f"Verified offline binary installation of conda {version}.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("assets", type=Path)
    parser.add_argument("version")
    args = parser.parse_args()
    prove_installers(args.assets, args.version)


if __name__ == "__main__":
    main()
