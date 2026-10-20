# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the shared health check utilities."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from conda.plugins.subcommands.doctor.health_checks.utils import (
    get_name_from_conda_meta_file_name,
    get_spec_str_from_conda_meta,
)

if TYPE_CHECKING:
    from pathlib import Path


def write_record(prefix: Path, stem: str, **fields) -> None:
    conda_meta = prefix / "conda-meta"
    conda_meta.mkdir(parents=True, exist_ok=True)
    (conda_meta / f"{stem}.json").write_text(json.dumps(fields))


def test_get_spec_str_from_conda_meta_empty(tmp_path: Path):
    """No packages yields no specs and nothing skipped."""
    assert get_spec_str_from_conda_meta(str(tmp_path), []) == ([], [])


def test_get_spec_str_from_conda_meta(tmp_path: Path):
    """Complete records are turned into name=version=build specs, in order."""
    write_record(tmp_path, "foo-1.0-py_0", name="foo", version="1.0", build="py_0")
    write_record(tmp_path, "bar-2.3-h123_1", name="bar", version="2.3", build="h123_1")

    specs, skipped = get_spec_str_from_conda_meta(
        str(tmp_path), ["foo-1.0-py_0", "bar-2.3-h123_1"]
    )

    assert specs == ["foo=1.0=py_0", "bar=2.3=h123_1"]
    assert skipped == []


@pytest.mark.parametrize("missing", ["name", "version", "build"])
def test_get_spec_str_from_conda_meta_missing_field(
    tmp_path: Path,
    missing: str,
):
    """Records missing a required field are skipped, logged and reported."""
    fields = {"name": "foo", "version": "1.0", "build": "py_0"}
    del fields[missing]
    write_record(tmp_path, "foo-1.0-py_0", **fields)
    write_record(tmp_path, "bar-2.3-h123_1", name="bar", version="2.3", build="h123_1")

    specs, skipped = get_spec_str_from_conda_meta(
        str(tmp_path), ["foo-1.0-py_0", "bar-2.3-h123_1"]
    )

    assert specs == ["bar=2.3=h123_1"]
    assert skipped == ["foo-1.0-py_0"]


def test_get_specs_from_non_existent_prefix():
    """Non-existent prefix raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        get_spec_str_from_conda_meta("idontexist", ["foo-1.0-py_0", "bar-2.3-h123_1"])


@pytest.mark.parametrize(
    "filename,expected",
    [
        pytest.param("foo-1.0-py_0.json", "foo", id="two-part-version-string"),
        pytest.param(
            "numpy-1.26.4-py312h8753938_0.json", "numpy", id="three-part-version-string"
        ),
        pytest.param(
            "python-dateutil-2.9.0-pyhd8ed1ab_0.json",
            "python-dateutil",
            id="hyphenated",
        ),
        pytest.param(
            "ruamel.yaml-0.18.6-py312h66e93f0_1.json", "ruamel.yaml", id="dotted-name"
        ),
        pytest.param(
            "_libgcc_mutex-0.1-conda_forge.json", "_libgcc_mutex", id="underscore"
        ),
        pytest.param(
            "/opt/env/conda-meta/foo-bar-1.0-0.json", "foo-bar", id="absolute-path"
        ),
        pytest.param("conda-meta/foo-1.0-0.json", "foo", id="relative-path"),
        pytest.param("foo-1.0-py_0", "foo", id="no-suffix"),
        pytest.param(
            "python-dateutil-2.9.0-pyhd8ed1ab_0",
            "python-dateutil",
            id="no-suffix-hyphenated",
        ),
    ],
)
def test_get_name_from_conda_meta_file_name(filename: str, expected: str):
    """The package name is everything before the trailing version and build."""
    assert get_name_from_conda_meta_file_name(filename) == expected
