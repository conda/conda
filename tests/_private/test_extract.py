# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Verify the extraction worker module stays import-light."""

from __future__ import annotations

import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from typing import TYPE_CHECKING

import pytest

from conda._private.extract import extract_conda_package_archive

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


class _UnpickleableError(Exception):
    def __init__(self, package_location: str, extract_location: str) -> None:
        super().__init__(f"Could not extract {package_location} to {extract_location}")


class _UnpickleableErrorPath:
    def __fspath__(self) -> str:
        raise _UnpickleableError("archive.conda", "destination")


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


def test_process_extract_normalizes_unpickleable_errors(tmp_path) -> None:
    with ProcessPoolExecutor(
        max_workers=1,
        mp_context=get_context("spawn"),
    ) as executor:
        future = executor.submit(
            extract_conda_package_archive,
            _UnpickleableErrorPath(),
            tmp_path,
            ensure_picklable_errors=True,
        )

        with pytest.raises(
            RuntimeError,
            match=r"_UnpickleableError: Could not extract archive\.conda to destination",
        ):
            future.result()


def test_extract_uses_standard_backoff(mocker: MockerFixture, tmp_path: Path) -> None:
    import conda_package_handling.api

    from conda.gateways import disk

    source = tmp_path / "package.conda"
    destination = tmp_path / "package"
    extract = mocker.patch.object(conda_package_handling.api, "extract")
    backoff = mocker.spy(disk, "exp_backoff_fn")

    extract_conda_package_archive(source, destination)

    backoff.assert_called_once_with(
        extract,
        str(source),
        dest_dir=str(destination),
    )
    extract.assert_called_once_with(str(source), dest_dir=str(destination))
