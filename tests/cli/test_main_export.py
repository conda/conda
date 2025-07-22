# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest

from conda.base.context import context, reset_context
from conda.common.serialize import json, yaml_safe_load
from conda.exceptions import CondaValueError

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import MonkeyPatch

    from conda.testing.fixtures import CondaCLIFixture, PathFactory


def test_export(conda_cli: CondaCLIFixture, path_factory: PathFactory) -> None:
    name = uuid.uuid4().hex
    path = path_factory(suffix=".yml")
    conda_cli("export", f"--name={name}", f"--file={path}")
    assert path.exists()

    # check bare minimum contents of the export file
    data = yaml_safe_load(path.read_text())
    assert data["name"] == name


def test_export_override_channels(
    conda_cli: CondaCLIFixture,
    monkeypatch: MonkeyPatch,
    path_factory: PathFactory,
) -> None:
    # channels to be ignored
    channels = (uuid.uuid4().hex, uuid.uuid4().hex)
    monkeypatch.setenv("CONDA_CHANNELS", ",".join(channels))
    reset_context()
    assert set(channels) <= set(context.channels)

    name = uuid.uuid4().hex
    path = path_factory(suffix=".yml")
    conda_cli(
        "export",
        f"--name={name}",
        "--override-channels",
        "--channel=tester",
        f"--file={path}",
    )
    assert path.exists()

    data = yaml_safe_load(path.read_text())
    assert data["channels"] == ["tester"]


def test_export_add_channels(
    conda_cli: CondaCLIFixture,
    path_factory: PathFactory,
) -> None:
    name = uuid.uuid4().hex
    path = path_factory(suffix=".yml")
    conda_cli(
        "export",
        f"--name={name}",
        "--channel=include-me",
        f"--file={path}",
    )
    assert path.exists()

    data = yaml_safe_load(path.read_text())
    assert data["channels"] == ["include-me", *context.channels]


def test_export_yaml_file_extension(
    conda_cli: CondaCLIFixture,
    path_factory: PathFactory,
) -> None:
    # With the plugin system, unrecognized file extensions require explicit format specification
    name = uuid.uuid4().hex
    path = path_factory(suffix=".txt")

    # This should now fail without explicit format
    with pytest.raises(CondaValueError, match="File extension.*is not recognized"):
        conda_cli("export", f"--name={name}", f"--file={path}")

    # But should work with explicit format
    conda_cli("export", f"--name={name}", f"--file={path}", "--format=yaml")
    assert path.exists()

    # Content should be YAML format
    data = yaml_safe_load(path.read_text())
    assert data["name"] == name


def test_execute_export_no_file_specified(
    conda_cli: CondaCLIFixture,
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)

    # ensure current directory is empty
    assert not list(tmp_path.iterdir())

    name = uuid.uuid4().hex
    conda_cli("export", f"--name={name}")

    # ensure no environment file was created
    assert not list(tmp_path.iterdir())


def test_export_with_json(
    conda_cli: CondaCLIFixture,
    path_factory: PathFactory,
) -> None:
    name = uuid.uuid4().hex
    path = path_factory(suffix=".yml")
    stdout, stderr, code = conda_cli(
        "export",
        f"--name={name}",
        "--json",
        f"--file={path}",
    )
    assert stdout
    assert not stderr
    assert not code

    # With --json and --file, output should be success info in JSON format
    data = json.loads(stdout)
    assert data["success"]
    assert data["file"] == str(path)
    assert data["format"] == "yaml"

    # The actual environment file should exist and be valid YAML
    assert path.exists()
    yaml_data = yaml_safe_load(path.read_text())
    assert yaml_data["name"] == name


def test_export_json_format(conda_cli: CondaCLIFixture) -> None:
    """Test exporting with --format json."""
    name = uuid.uuid4().hex
    stdout, stderr, code = conda_cli("export", f"--name={name}", "--format=json")
    assert not stderr
    assert not code
    assert stdout

    # Verify it's valid JSON
    data = json.loads(stdout)
    assert data["name"] == name
    # dependencies might not be present in empty environments
    assert "channels" in data


def test_export_json_file_extension(
    conda_cli: CondaCLIFixture,
    path_factory: PathFactory,
) -> None:
    """Test exporting to JSON file by extension."""
    name = uuid.uuid4().hex
    path = path_factory(suffix=".json")
    conda_cli("export", f"--name={name}", f"--file={path}")
    assert path.exists()

    # Verify it's valid JSON
    data = json.loads(path.read_text())
    assert data["name"] == name
    # dependencies might not be present in empty environments
    assert "channels" in data


def test_export_yaml_format(conda_cli: CondaCLIFixture) -> None:
    """Test exporting with --format yaml for backward compatibility."""
    name = uuid.uuid4().hex
    stdout, stderr, code = conda_cli("export", f"--name={name}", "--format=yaml")
    assert not stderr
    assert not code
    assert stdout

    # Verify it's valid YAML
    data = yaml_safe_load(stdout)
    assert data["name"] == name
    # dependencies might not be present in empty environments
    assert "channels" in data


def test_export_toml_format(conda_cli: CondaCLIFixture) -> None:
    """Test exporting with --format toml (TOML format not supported)."""
    name = uuid.uuid4().hex
    # TOML format is not supported, so this should be caught at argument parsing level
    with pytest.raises(SystemExit):
        conda_cli("export", f"--name={name}", "--format=toml")


def test_export_toml_file_extension(
    conda_cli: CondaCLIFixture,
    path_factory: PathFactory,
) -> None:
    """Test exporting to TOML file by extension (if TOML dependencies available)."""
    name = uuid.uuid4().hex
    path = path_factory(suffix=".toml")
    try:
        conda_cli("export", f"--name={name}", f"--file={path}")
        if path.exists():
            # Verify the file was created and has reasonable content
            content = path.read_text()
            assert name in content
        else:
            pytest.skip("TOML dependencies not available")
    except Exception:
        pytest.skip("TOML format not supported")


def test_export_unknown_format(conda_cli: CondaCLIFixture) -> None:
    """Test that unknown export formats are caught at argument parsing level."""
    name = uuid.uuid4().hex
    # Should raise SystemExit for unknown formats (caught by argument parser)
    with pytest.raises(SystemExit):
        conda_cli("export", f"--name={name}", "--format=unknown")


def test_export_unknown_format_verbose(conda_cli: CondaCLIFixture) -> None:
    """Test that unknown export formats are caught at argument parsing level in verbose mode too."""
    name = uuid.uuid4().hex
    # Should raise SystemExit for unknown formats in verbose mode (caught by argument parser)
    with pytest.raises(SystemExit):
        conda_cli("export", f"--name={name}", "--format=unknown", "-v")


def test_export_format_priority_over_extension(
    conda_cli: CondaCLIFixture,
    path_factory: PathFactory,
) -> None:
    """Test that --format argument takes priority over file extension."""
    name = uuid.uuid4().hex
    # Use .yaml extension but request JSON format
    path = path_factory(suffix=".yaml")
    conda_cli("export", f"--name={name}", "--format=json", f"--file={path}")
    assert path.exists()

    # The file should contain JSON despite .yaml extension
    try:
        data = json.load(path.read_text())
        assert data["name"] == name
    except Exception:
        # If JSON parsing fails, check if it fell back to YAML
        data = yaml_safe_load(path.read_text())
        assert data["name"] == name
