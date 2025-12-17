# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Shared fixtures for doctor and fix subcommand tests."""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path


@pytest.fixture(params=[".pyo", ".pyc"])
def env_ok(tmp_path: Path, request) -> Iterable[tuple[Path, str, str, str, str]]:
    """Fixture that returns a testing environment with no missing files.

    Used by both health check (doctor) and health fix tests.

    Returns:
        Tuple of (prefix, bin_file, lib_file, ignored_file, package_name)
    """
    package = uuid.uuid4().hex

    (tmp_path / "bin").mkdir(parents=True, exist_ok=True)
    (tmp_path / "lib").mkdir(parents=True, exist_ok=True)
    (tmp_path / "pycache").mkdir(parents=True, exist_ok=True)
    (tmp_path / "conda-meta").mkdir(parents=True, exist_ok=True)

    bin_file = f"bin/{package}"
    (tmp_path / bin_file).touch()

    lib_file = f"lib/{package}.py"
    (tmp_path / lib_file).touch()

    ignored_file = f"pycache/{package}.{request.param}"
    (tmp_path / ignored_file).touch()

    # SHA256 for empty file
    empty_sha256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    PACKAGE_JSON = {
        "files": [bin_file, lib_file, ignored_file],
        "paths_data": {
            "paths": [
                {
                    "_path": bin_file,
                    "sha256": empty_sha256,
                    "sha256_in_prefix": empty_sha256,
                },
                {
                    "_path": lib_file,
                    "sha256": empty_sha256,
                    "sha256_in_prefix": empty_sha256,
                },
                {
                    "_path": ignored_file,
                    "sha256": empty_sha256,
                    "sha256_in_prefix": empty_sha256,
                },
            ],
            "paths_version": 1,
        },
    }

    (tmp_path / "conda-meta" / f"{package}.json").write_text(json.dumps(PACKAGE_JSON))

    yield tmp_path, bin_file, lib_file, ignored_file, package


@pytest.fixture
def env_missing_files(
    env_ok: tuple[Path, str, str, str, str],
) -> tuple[Path, str, str, str, str]:
    """Fixture that returns a testing environment with missing files.

    Used by both health check (doctor) and health fix tests.
    """
    prefix, bin_file, _, ignored_file, _ = env_ok
    (prefix / bin_file).unlink()
    (prefix / ignored_file).unlink()
    return env_ok


@pytest.fixture
def env_altered_files(
    env_ok: tuple[Path, str, str, str, str],
) -> tuple[Path, str, str, str, str]:
    """Fixture that returns a testing environment with altered files.

    Used by both health check (doctor) and health fix tests.
    """
    prefix, _, lib_file, ignored_file, _ = env_ok
    with open(prefix / lib_file, "w") as f:
        f.write("print('Hello, World!')")
    with open(prefix / ignored_file, "w") as f:
        f.write("nonsense")
    return env_ok

