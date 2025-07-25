# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Test conda export."""

import json
import uuid
from pathlib import Path

import pytest

from conda.base.context import context
from conda.common.serialize import yaml_safe_load
from conda.exceptions import (
    ArgumentError,
    CondaValueError,
    EnvironmentExporterNotDetected,
)
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
    """Test export with override channels requires channel specification."""
    name = uuid.uuid4().hex
    path = tmp_path / "environment.yaml"  # Use exact default filename

    # Using --override-channels without specifying channels should raise ArgumentError
    with pytest.raises(
        ArgumentError,
        match="At least one -c / --channel flag must be supplied when using --override-channels",
    ):
        conda_cli(
            "export",
            f"--name={name}",
            "--override-channels",
            f"--file={path}",
        )


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


@pytest.mark.parametrize(
    "format_name,parser_func",
    [
        ("environment-yaml", yaml_safe_load),
        ("environment-json", json.loads),
        ("yaml", yaml_safe_load),  # Test alias
        ("json", json.loads),  # Test alias
    ],
)
def test_export_format_to_stdout(conda_cli: CondaCLIFixture, format_name, parser_func):
    """Test exporting with different formats to stdout (canonical names and aliases)."""
    name = uuid.uuid4().hex
    stdout, stderr, code = conda_cli(
        "export", f"--name={name}", f"--format={format_name}"
    )
    assert not stderr
    assert not code
    assert stdout

    # Parse with appropriate parser and verify content
    parsed_data = parser_func(stdout)
    assert parsed_data["name"] == name


@pytest.mark.parametrize(
    "filename,parser_func",
    [
        ("environment.yaml", yaml_safe_load),
        ("environment.yml", yaml_safe_load),
        ("environment.json", json.loads),
    ],
)
def test_export_structured_file_extension_detection(
    conda_cli: CondaCLIFixture, tmp_path: Path, filename, parser_func
):
    """Test export with structured format file extension detection."""
    name = uuid.uuid4().hex
    path = tmp_path / filename

    conda_cli("export", f"--name={name}", f"--file={path}")
    assert path.exists()

    # Parse with appropriate parser and verify content
    parsed_data = parser_func(path.read_text())
    assert parsed_data["name"] == name


@pytest.mark.parametrize(
    "format_name,expected_error_fragment",
    [
        ("explicit", "Cannot export explicit format"),
        ("requirements", "Cannot export requirements format"),
        ("reqs", "Cannot export requirements format"),  # Test alias
        ("txt", "Cannot export requirements format"),  # Test alias
    ],
)
def test_export_text_formats_fail_on_empty_environments(
    conda_cli: CondaCLIFixture, format_name, expected_error_fragment
):
    """Test that text-based formats appropriately fail for empty environments."""
    name = uuid.uuid4().hex

    # These formats should fail because empty environments have no package data
    with pytest.raises(CondaValueError, match=expected_error_fragment):
        conda_cli("export", f"--name={name}", f"--format={format_name}")


@pytest.mark.parametrize(
    "filename,expected_error_fragment",
    [
        ("explicit.txt", "Cannot export explicit format"),
        ("requirements.txt", "Cannot export requirements format"),
        ("spec.txt", "Cannot export requirements format"),
    ],
)
def test_export_text_file_extensions_fail_on_empty_environments(
    conda_cli: CondaCLIFixture, tmp_path: Path, filename, expected_error_fragment
):
    """Test that text-based file extensions appropriately fail for empty environments."""
    name = uuid.uuid4().hex
    path = tmp_path / filename

    # These should fail because empty environments have no package data
    with pytest.raises(CondaValueError, match=expected_error_fragment):
        conda_cli("export", f"--name={name}", f"--file={path}")


@pytest.mark.parametrize(
    "format_name,expected_exception",
    [
        ("toml", SystemExit),  # Unsupported format
        ("unknown", SystemExit),  # Unknown format
    ],
)
def test_export_unsupported_formats(
    conda_cli: CondaCLIFixture, format_name, expected_exception
):
    """Test that unsupported/unknown formats raise appropriate errors."""
    name = uuid.uuid4().hex
    with pytest.raises(expected_exception):
        conda_cli("export", f"--name={name}", f"--format={format_name}")


def test_export_unrecognized_file_extension(
    conda_cli: CondaCLIFixture, tmp_path: Path
) -> None:
    """Test that unrecognized filename requires explicit format."""
    name = uuid.uuid4().hex
    path = tmp_path / "environment.toml"  # Non-default filename

    # Should fail because filename is not recognized
    with pytest.raises(
        EnvironmentExporterNotDetected, match="No environment exporter plugin found"
    ):
        conda_cli("export", f"--name={name}", f"--file={path}")

    # Should work with explicit format
    conda_cli("export", f"--name={name}", f"--file={path}", "--format=environment-yaml")
    assert path.exists()


def test_export_unknown_format_verbose(conda_cli: CondaCLIFixture) -> None:
    """Test that unknown format with verbose shows appropriate error."""
    name = uuid.uuid4().hex
    with pytest.raises(SystemExit):
        conda_cli("export", f"--name={name}", "--format=unknown", "-v")


def test_export_format_consistency(conda_cli: CondaCLIFixture) -> None:
    """Test that CLI choices and error messages use the same format source."""
    # Plugin manager should be the single source of truth for available formats
    available_formats = sorted(context.plugin_manager.get_exporter_format_mapping())

    # Verify the function returns both canonical names and aliases
    canonical_formats = {"environment-yaml", "environment-json", "explicit"}
    alias_formats = {"yaml", "json"}

    available_set = set(available_formats)

    assert canonical_formats.issubset(available_set), "Missing canonical format names"
    assert alias_formats.issubset(available_set), "Missing user-friendly aliases"


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


def test_export_json_flag_backwards_compatibility(conda_cli: CondaCLIFixture) -> None:
    """Test that --json without --format outputs JSON (backwards compatibility)."""
    name = uuid.uuid4().hex
    stdout, stderr, code = conda_cli("export", f"--name={name}", "--json")
    assert not stderr
    assert not code
    assert stdout

    # Should output JSON format for backwards compatibility
    json_data = json.loads(stdout)
    assert json_data["name"] == name


@pytest.mark.parametrize(
    "format_name,expected_result",
    [
        ("environment-yaml", ("contains", "name: ")),
        ("yaml", ("contains", "name: ")),
        ("explicit", ("raises", "Cannot export explicit format")),
    ],
)
def test_export_format_precedence_over_json_flag(
    conda_cli: CondaCLIFixture, format_name, expected_result
) -> None:
    """Test that --format takes precedence over --json flag for content."""
    name = uuid.uuid4().hex
    result_type, result_value = expected_result

    if result_type == "contains":
        # Should output the specified format, not JSON
        stdout, stderr, code = conda_cli(
            "export", f"--name={name}", f"--format={format_name}", "--json"
        )
        assert not stderr
        assert not code
        assert stdout
        assert result_value in stdout

        # Should not be JSON format
        with pytest.raises((json.JSONDecodeError, ValueError)):
            json.loads(stdout)

    elif result_type == "raises":
        # Should fail with the specified format error, not try JSON
        with pytest.raises(CondaValueError, match=result_value):
            conda_cli("export", f"--name={name}", f"--format={format_name}", "--json")


@pytest.mark.parametrize(
    "filename,expected_result",
    [
        ("environment.yaml", ("success", "name: ")),
        ("environment.json", ("success", '"name":')),
        ("explicit.txt", ("raises", "Cannot export explicit format")),
    ],
)
def test_export_file_with_json_flag_behavior(
    conda_cli: CondaCLIFixture, tmp_path: Path, filename, expected_result
) -> None:
    """Test --json with --file behavior: status messages for successful formats, appropriate failures for others."""
    name = uuid.uuid4().hex
    path = tmp_path / filename
    result_type, result_value = expected_result

    if result_type == "success":
        # Should write to file and output JSON status
        stdout, stderr, code = conda_cli(
            "export", f"--name={name}", f"--file={path}", "--json"
        )
        assert not stderr
        assert not code
        assert path.exists()

        # Stdout should contain JSON status message
        status_data = json.loads(stdout)
        assert status_data["success"] is True
        assert status_data["file"] == str(path)

        # File content should match the format determined by extension
        file_content = path.read_text()
        assert result_value in file_content

    elif result_type == "raises":
        # Should fail with the specified error, not try to output JSON
        with pytest.raises(CondaValueError, match=result_value):
            conda_cli("export", f"--name={name}", f"--file={path}", "--json")


def test_export_json_flag_with_file_no_format_detection_error(
    conda_cli: CondaCLIFixture, tmp_path: Path
) -> None:
    """Test --json with unrecognized file extension shows appropriate error."""
    name = uuid.uuid4().hex
    path = tmp_path / "test.unknown"

    # Should fail with environment exporter not detected error
    with pytest.raises(
        EnvironmentExporterNotDetected, match="No environment exporter plugin found"
    ):
        conda_cli("export", f"--name={name}", f"--file={path}", "--json")


def test_export_preserves_channels_from_installed_packages(
    conda_cli: CondaCLIFixture,
) -> None:
    """Test that conda export includes channels from installed packages."""
    stdout, stderr, code = conda_cli("export", "--format=environment-yaml")
    assert not stderr
    assert not code
    assert stdout

    # Parse the YAML output
    env_data = yaml_safe_load(stdout)

    # Should have channels section
    assert "channels" in env_data
    assert isinstance(env_data["channels"], list)
    assert len(env_data["channels"]) > 0

    # Test environment typically has conda-forge and/or defaults
    # Just verify we have reasonable channels present
    channels = env_data["channels"]
    expected_channels = {"conda-forge", "defaults"}
    found_channels = set(channels) & expected_channels

    assert len(found_channels) > 0, (
        f"Expected to find conda-forge or defaults in channels: {channels}"
    )


@pytest.mark.parametrize("ignore_channels", [True, False])
def test_export_ignore_channels_flag(
    conda_cli: CondaCLIFixture, ignore_channels
) -> None:
    """Test that --ignore-channels affects channel extraction."""
    args = ["export", "--format=environment-yaml"]
    if ignore_channels:
        args.append("--ignore-channels")

    stdout, stderr, code = conda_cli(*args)
    assert not stderr
    assert not code
    assert stdout

    env_data = yaml_safe_load(stdout)

    if ignore_channels:
        # With --ignore-channels, should still have channels (from context.channels)
        # but package-specific channels should not be extracted
        assert "channels" in env_data
        # Dependencies should not include channel prefixes
        for dep in env_data.get("dependencies", []):
            if isinstance(dep, str):
                assert "::" not in dep, f"Found channel prefix in dependency: {dep}"
    else:
        # Without --ignore-channels, should have channels and may include channel prefixes
        assert "channels" in env_data
        assert len(env_data["channels"]) > 0
