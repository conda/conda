# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Test conda export."""

import json
import uuid
from pathlib import Path

import pytest

from conda.common.serialize import yaml_safe_load
from conda.exceptions import CondaValueError
from conda.testing.fixtures import CondaCLIFixture


def test_export(conda_cli: CondaCLIFixture) -> None:
    """Test default export behavior - should export as YAML to stdout."""
    name = uuid.uuid4().hex
    stdout, stderr, code = conda_cli("export", f"--name={name}")
    assert not stderr
    assert not code
    assert stdout

    # Verify the output is valid YAML
    yaml_data = yaml_safe_load(stdout)
    assert yaml_data["name"] == name


def test_export_override_channels(conda_cli: CondaCLIFixture, tmp_path: Path) -> None:
    """Test export with override channels."""
    name = uuid.uuid4().hex
    path = tmp_path / "environment.yaml"  # Use exact default filename

    conda_cli(
        "export",
        f"--name={name}",
        "--override-channels",
        f"--file={path}",
    )
    assert path.exists()

    data = yaml_safe_load(path.read_text())
    assert data["name"] == name


def test_export_add_channels(conda_cli: CondaCLIFixture, tmp_path: Path) -> None:
    """Test export with additional channels."""
    name = uuid.uuid4().hex
    path = tmp_path / "environment.yaml"  # Use exact default filename

    conda_cli(
        "export",
        f"--name={name}",
        "-c",
        "defaults",
        f"--file={path}",
    )
    assert path.exists()

    data = yaml_safe_load(path.read_text())
    assert data["name"] == name


def test_export_yaml_file_extension(conda_cli: CondaCLIFixture, tmp_path: Path) -> None:
    """Test export with YAML file using exact filename match."""
    name = uuid.uuid4().hex
    path = tmp_path / "environment.yaml"  # Use exact default filename

    # This should work without explicit format because filename is recognized
    conda_cli("export", f"--name={name}", f"--file={path}")
    assert path.exists()

    # Content should be YAML format
    data = yaml_safe_load(path.read_text())
    assert data["name"] == name

    # Test with .yml extension too
    path_yml = tmp_path / "environment.yml"
    conda_cli("export", f"--name={name}", f"--file={path_yml}")
    assert path_yml.exists()


def test_execute_export_no_file_specified(conda_cli: CondaCLIFixture) -> None:
    """Test that missing default format works (should default to environment-yaml)."""
    name = uuid.uuid4().hex
    stdout, stderr, code = conda_cli("export", f"--name={name}")
    assert not stderr
    assert not code
    assert stdout

    # Should be YAML format
    yaml_data = yaml_safe_load(stdout)
    assert yaml_data["name"] == name


def test_export_with_json(conda_cli: CondaCLIFixture, tmp_path: Path) -> None:
    """Test JSON export using exact filename."""
    name = uuid.uuid4().hex
    path = tmp_path / "environment.json"  # Use exact default filename

    stdout, stderr, code = conda_cli(
        "export",
        f"--name={name}",
        f"--file={path}",
    )
    assert not stderr
    assert not code
    assert path.exists()

    # Verify it's valid JSON
    json_data = json.loads(path.read_text())
    assert json_data["name"] == name


def test_export_json_format(conda_cli: CondaCLIFixture) -> None:
    """Test exporting with --format environment-json."""
    name = uuid.uuid4().hex
    stdout, stderr, code = conda_cli(
        "export", f"--name={name}", "--format=environment-json"
    )
    assert not stderr
    assert not code
    assert stdout

    # Verify it's valid JSON
    json_data = json.loads(stdout)
    assert json_data["name"] == name


def test_export_json_file_extension(conda_cli: CondaCLIFixture, tmp_path: Path) -> None:
    """Test export with JSON file using exact filename."""
    name = uuid.uuid4().hex
    path = tmp_path / "environment.json"  # Use exact default filename

    conda_cli("export", f"--name={name}", f"--file={path}")
    assert path.exists()

    json_data = json.loads(path.read_text())
    assert json_data["name"] == name


def test_export_yaml_format(conda_cli: CondaCLIFixture) -> None:
    """Test exporting with --format environment-yaml."""
    name = uuid.uuid4().hex
    stdout, stderr, code = conda_cli(
        "export", f"--name={name}", "--format=environment-yaml"
    )
    assert not stderr
    assert not code
    assert stdout

    yaml_data = yaml_safe_load(stdout)
    assert yaml_data["name"] == name


def test_export_yaml_alias(conda_cli: CondaCLIFixture) -> None:
    """Test exporting with --format yaml (alias)."""
    name = uuid.uuid4().hex
    stdout, stderr, code = conda_cli("export", f"--name={name}", "--format=yaml")
    assert not stderr
    assert not code
    assert stdout

    yaml_data = yaml_safe_load(stdout)
    assert yaml_data["name"] == name


def test_export_json_alias(conda_cli: CondaCLIFixture) -> None:
    """Test exporting with --format json (alias)."""
    name = uuid.uuid4().hex
    stdout, stderr, code = conda_cli("export", f"--name={name}", "--format=json")
    assert not stderr
    assert not code
    assert stdout

    # Verify it's valid JSON
    json_data = json.loads(stdout)
    assert json_data["name"] == name


def test_export_toml_format(conda_cli: CondaCLIFixture) -> None:
    """Test that unsupported format raises appropriate error."""
    name = uuid.uuid4().hex
    with pytest.raises(SystemExit):
        conda_cli("export", f"--name={name}", "--format=toml")


def test_export_toml_file_extension(conda_cli: CondaCLIFixture, tmp_path: Path) -> None:
    """Test that unrecognized filename requires explicit format."""
    name = uuid.uuid4().hex
    path = tmp_path / "environment.toml"  # Non-default filename

    # Should fail because filename is not recognized
    with pytest.raises(CondaValueError, match="Filename.*is not recognized"):
        conda_cli("export", f"--name={name}", f"--file={path}")

    # Should work with explicit format
    conda_cli("export", f"--name={name}", f"--file={path}", "--format=environment-yaml")
    assert path.exists()


def test_export_unknown_format(conda_cli: CondaCLIFixture) -> None:
    """Test that unknown format raises appropriate error."""
    name = uuid.uuid4().hex
    with pytest.raises(SystemExit):
        conda_cli("export", f"--name={name}", "--format=unknown")


def test_export_unknown_format_verbose(conda_cli: CondaCLIFixture) -> None:
    """Test that unknown format with verbose shows appropriate error."""
    name = uuid.uuid4().hex
    with pytest.raises(SystemExit):
        conda_cli("export", f"--name={name}", "--format=unknown", "-v")


def test_export_format_priority_over_extension(
    conda_cli: CondaCLIFixture, tmp_path: Path
) -> None:
    """Test that explicit format takes priority over filename detection."""
    name = uuid.uuid4().hex
    path = tmp_path / "environment.yaml"  # YAML filename

    # Should export as JSON despite YAML filename
    conda_cli("export", f"--name={name}", "--format=environment-json", f"--file={path}")
    assert path.exists()

    # Content should be JSON format despite .yaml extension
    json_data = json.loads(path.read_text())
    assert json_data["name"] == name
