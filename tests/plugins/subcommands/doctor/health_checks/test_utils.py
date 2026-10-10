# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the shared health check utilities."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import pytest

from conda.plugins.subcommands.doctor.health_checks.utils import (
    get_specs_from_conda_meta,
)

if TYPE_CHECKING:
    from pathlib import Path


def write_record(prefix: Path, stem: str, **fields) -> None:
    conda_meta = prefix / "conda-meta"
    conda_meta.mkdir(parents=True, exist_ok=True)
    (conda_meta / f"{stem}.json").write_text(json.dumps(fields))


def test_get_specs_from_conda_meta_empty(tmp_path: Path):
    """No packages yields no specs and nothing skipped."""
    assert get_specs_from_conda_meta(str(tmp_path), []) == ([], [])


def test_get_specs_from_conda_meta(tmp_path: Path):
    """Complete records are turned into name=version=build specs, in order."""
    write_record(tmp_path, "foo-1.0-py_0", name="foo", version="1.0", build="py_0")
    write_record(tmp_path, "bar-2.3-h123_1", name="bar", version="2.3", build="h123_1")

    specs, skipped = get_specs_from_conda_meta(
        str(tmp_path), ["foo-1.0-py_0", "bar-2.3-h123_1"]
    )

    assert specs == ["foo=1.0=py_0", "bar=2.3=h123_1"]
    assert skipped == []


@pytest.mark.parametrize("missing", ["name", "version", "build"])
def test_get_specs_from_conda_meta_missing_field(
    tmp_path: Path,
    capsys: pytest.CaptureFixture,
    caplog: pytest.LogCaptureFixture,
    missing: str,
):
    """Records missing a required field are skipped, logged and reported."""
    fields = {"name": "foo", "version": "1.0", "build": "py_0"}
    del fields[missing]
    write_record(tmp_path, "foo-1.0-py_0", **fields)
    write_record(tmp_path, "bar-2.3-h123_1", name="bar", version="2.3", build="h123_1")

    with caplog.at_level(logging.ERROR):
        specs, skipped = get_specs_from_conda_meta(
            str(tmp_path), ["foo-1.0-py_0", "bar-2.3-h123_1"]
        )

    assert specs == ["bar=2.3=h123_1"]
    assert skipped == ["foo-1.0-py_0"]
    assert f"missing field '{missing}'" in caplog.text
    assert "foo-1.0-py_0" in caplog.text
    assert (
        "Reinstalling package foo-1.0-py_0 failed due to missing fields"
        in capsys.readouterr().out
    )


def test_get_specs_from_non_existent_prefix():
    """Non-existent prefix raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        get_specs_from_conda_meta("idontexist", ["foo-1.0-py_0", "bar-2.3-h123_1"])
