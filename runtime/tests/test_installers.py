# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import importlib.util
import os
import platform
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT_ROOT = Path(__file__).parents[1] / "scripts"


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPT_ROOT / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


proof = load_script("prove-installers")
artifacts = load_script("verify-runtime-artifacts")


@pytest.fixture
def assets(tmp_path, monkeypatch):
    if os.name == "nt":
        pytest.skip("POSIX executable fixture, Windows proof uses the built executable")
    target = proof.TARGETS[(platform.system(), platform.machine())]
    release_assets = tmp_path / "release-assets"
    release_assets.mkdir()
    for name, contents in artifacts.render_installers("99.0.0").items():
        (release_assets / name).write_bytes(contents)
    helper = tmp_path / "record.py"
    helper.write_text(
        """import json
import os
import pathlib
import sys

if sys.argv[1:] == ["--version"]:
    print("conda 99.0.0")
    sys.exit(0)
if os.environ.get("INSTALLER_FAIL"):
    sys.exit(1)
assert os.environ["CONDA_SHIP_INTERNAL_UPDATE"] == "v1/record-installation"
assert "CONDA_SHIP_INTERNAL_UPDATE_INSTRUCTION" not in os.environ
prefix = pathlib.Path(os.environ["CONDA_SHIP_PREFIX"])
prefix.mkdir(parents=True)
(prefix / ".conda.json").write_text(json.dumps({"update": {
    "ownership": os.environ["CONDA_SHIP_INTERNAL_UPDATE_OWNERSHIP"],
    "installation": os.environ["CONDA_SHIP_INTERNAL_UPDATE_INSTALLATION"],
    "executable": os.environ["CONDA_SHIP_INTERNAL_UPDATE_EXECUTABLE"],
    "package": "conda-runtime"
}}))
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("INSTALLER_PROOF_PYTHON", sys.executable)
    monkeypatch.setenv("INSTALLER_PROOF_HELPER", str(helper))
    executable = release_assets / f"conda-{target}"
    executable.write_text(
        '#!/bin/sh\nexec "$INSTALLER_PROOF_PYTHON" "$INSTALLER_PROOF_HELPER" "$@"\n',
        encoding="utf-8",
    )
    (release_assets / "SHA256SUMS").write_text(
        f"{proof.sha256(executable)}  {executable.name}\n", encoding="utf-8"
    )
    return release_assets


def test_installer_records_ownership_and_preserves_existing_executable(assets):
    proof.prove_installers(assets, "99.0.0")


@pytest.mark.parametrize("failure", ["checksum", "registration"])
def test_failed_installation_leaves_no_executable(tmp_path, assets, failure):
    root = tmp_path / "proof"
    root.mkdir()
    destination = root / "bin/conda"
    env = os.environ | {
        "RELEASE_ASSETS": str(assets),
        "INSTALL_DIR": str(destination.parent),
        "CONDA_SHIP_PREFIX": str(root / "prefix"),
        "CONDA_SHIP_INTERNAL_UPDATE_INSTRUCTION": "discard inherited instruction",
    }
    if failure == "checksum":
        checksum = (assets / "SHA256SUMS").read_text()
        (assets / "SHA256SUMS").write_text("0" * 64 + checksum[64:])
    else:
        env["INSTALLER_FAIL"] = "1"
    command = proof.installer_command(root, assets, env)
    result = subprocess.run(command, env=env, capture_output=True, text=True)
    assert result.returncode != 0, result.stderr
    assert not destination.exists()


def test_rendered_installers_download_the_matching_official_release():
    for installer in artifacts.render_installers("99.0.0").values():
        assert b"https://github.com/conda/conda" in installer
        assert b"99.0.0" in installer
        assert b"@CONDA_RUNTIME_VERSION@" not in installer
