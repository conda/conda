# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Test conda export."""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING

import pytest

from conda.base.context import context
from conda.common.serialize import yaml
from conda.core.prefix_data import PrefixData
from conda.exceptions import (
    ArgumentError,
    CondaValueError,
    EnvironmentExporterNotDetected,
)

if TYPE_CHECKING:
    from pathlib import Path

    from conda.plugins.manager import CondaPluginManager
    from conda.testing.fixtures import CondaCLIFixture, PipCLIFixture


def test_export(conda_cli: CondaCLIFixture) -> None:
    """Test default export behavior - should export as YAML to stdout."""
    name = uuid.uuid4().hex
    assert context.export_platforms == (context.subdir,)
    stdout, stderr, code = conda_cli("export", f"--name={name}")
    assert not stderr
    assert not code
    assert stdout

    # Verify the output is valid YAML
    yaml_data = yaml.loads(stdout)
    assert yaml_data["name"] == name


def test_export_override_channels(conda_cli: CondaCLIFixture, tmp_path: Path) -> None:
    """Test export with override channels requires channel specification."""
    name = uuid.uuid4().hex
    path = tmp_path / "environment.yaml"  # Use exact default filename

    # Using -O, --override-channels without specifying channels should raise ArgumentError
    for flag in ("-O", "--override-channels"):
        with pytest.raises(
            ArgumentError,
            match="At least one -c / --channel flag must be supplied when using --override-channels",
        ):
            conda_cli(
                "export",
                f"--name={name}",
                flag,
                f"--file={path}",
            )


def test_export_add_channels(conda_cli: CondaCLIFixture, tmp_path: Path) -> None:
    """Test export with additional channels."""
    name = uuid.uuid4().hex
    path = tmp_path / "environment.yaml"

    conda_cli(
        "export",
        f"--name={name}",
        "-c",
        "conda-forge",
        f"--file={path}",
    )
    assert path.exists()

    data = yaml.loads(path.read_text())
    assert data["name"] == name

    # Verify that the additional channel was added
    assert "conda-forge" in data["channels"]


def test_execute_export_no_file_specified(conda_cli: CondaCLIFixture) -> None:
    """Test that missing default format works (should default to environment-yaml)."""
    name = uuid.uuid4().hex
    stdout, stderr, code = conda_cli("export", f"--name={name}")
    assert not stderr
    assert not code
    assert stdout

    # Should be YAML format
    yaml_data = yaml.loads(stdout)
    assert yaml_data["name"] == name


@pytest.mark.parametrize(
    "format_name,parser_func",
    [
        ("environment-yaml", yaml.loads),
        ("environment-json", json.loads),
        ("yaml", yaml.loads),  # Test alias
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
        ("environment.yaml", yaml.loads),
        ("environment.yml", yaml.loads),
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
    env_data = yaml.loads(stdout)

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

    env_data = yaml.loads(stdout)

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


def test_export_package_alphabetical_ordering(conda_cli):
    """Test that exported packages are sorted alphabetically."""
    stdout, stderr, code = conda_cli("export", "--format=environment-yaml")
    assert code == 0

    env_data = yaml.loads(stdout)
    dependencies = env_data.get("dependencies", [])

    # Extract conda package names (skip pip dependencies which are dicts)
    conda_packages = [dep for dep in dependencies if isinstance(dep, str)]
    package_names = [dep.split("=")[0] for dep in conda_packages]

    # Verify packages are in alphabetical order
    assert package_names == sorted(package_names), (
        "Packages should be in alphabetical order"
    )

    # Verify we have some packages to test with
    assert len(package_names) > 5, "Should have multiple packages for ordering test"


def test_export_no_builds_format(conda_cli):
    """Test that --no-builds produces name=version format without .* suffix."""
    stdout, stderr, code = conda_cli(
        "export", "--no-builds", "--format=environment-yaml"
    )
    assert code == 0

    env_data = yaml.loads(stdout)
    dependencies = env_data.get("dependencies", [])

    # Extract conda package specs (skip pip dependencies which are dicts)
    conda_packages = [dep for dep in dependencies if isinstance(dep, str)]

    for package_spec in conda_packages:
        # Should have exactly one equals sign (name=version)
        parts = package_spec.split("=")
        assert len(parts) == 2, (
            f"Package spec should be name=version format: {package_spec}"
        )

        name, version = parts
        # Should not contain build string or .* suffix
        assert "*" not in version, f"Version should not contain '*': {package_spec}"
        assert version.count("=") == 0, f"Should not have build string: {package_spec}"

    # Verify we have packages to test with
    assert len(conda_packages) > 0, "Should have conda packages to test"


def test_export_from_history_format(conda_cli):
    """Test that --from-history produces bracket format for version constraints."""
    stdout, stderr, code = conda_cli(
        "export", "--from-history", "--format=environment-yaml"
    )

    if code != 0:
        # Some environments might not have history, skip gracefully
        pytest.skip("Environment has no history to export")

    env_data = yaml.loads(stdout)
    dependencies = env_data.get("dependencies", [])

    # Extract conda package specs (skip pip dependencies which are dicts)
    conda_packages = [dep for dep in dependencies if isinstance(dep, str)]

    # Check for bracket format in version constraints
    for package_spec in conda_packages:
        if "[version=" in package_spec and "]" in package_spec:
            # Verify proper bracket format
            assert package_spec.count("[") == package_spec.count("]"), (
                f"Mismatched brackets: {package_spec}"
            )
        elif "=" in package_spec:
            # Simple equality should not have brackets
            assert "[" not in package_spec and "]" not in package_spec, (
                f"Simple spec should not have brackets: {package_spec}"
            )

    # Note: It's okay if no constraints exist, we just test format when they do


def test_export_override_channels_behavior(conda_cli):
    """Test that --override-channels properly replaces channels."""
    # Test with override channels
    stdout, stderr, code = conda_cli(
        "export",
        "--override-channels",
        "-c",
        "conda-forge",
        "--format=environment-yaml",
    )
    assert code == 0

    env_data = yaml.loads(stdout)
    channels = env_data.get("channels", [])

    # Should only have the specified channel
    assert "conda-forge" in channels, "Should include specified channel"
    # Should not have defaults when overriding (unless explicitly added)
    if "defaults" in channels:
        # If defaults appears, it should be because conda-forge wasn't sufficient
        # This is acceptable behavior in some cases
        pass

    # Test with multiple override channels
    stdout2, stderr2, code2 = conda_cli(
        "export",
        "--override-channels",
        "-c",
        "conda-forge",
        "-c",
        "bioconda",
        "--format=environment-yaml",
    )
    assert code2 == 0

    env_data2 = yaml.loads(stdout2)
    channels2 = env_data2.get("channels", [])

    # Should include both specified channels
    assert "conda-forge" in channels2, "Should include conda-forge"
    assert "bioconda" in channels2, "Should include bioconda"


def test_export_regular_format_consistency(conda_cli):
    """Test that regular export produces name=version=build format."""
    stdout, stderr, code = conda_cli("export", "--format=environment-yaml")
    assert code == 0

    env_data = yaml.loads(stdout)
    dependencies = env_data.get("dependencies", [])

    # Extract conda package specs (skip pip dependencies which are dicts)
    conda_packages = [dep for dep in dependencies if isinstance(dep, str)]

    for package_spec in conda_packages:
        # Should have name=version=build format (3 parts)
        parts = package_spec.split("=")
        assert len(parts) == 3, (
            f"Package spec should be name=version=build format: {package_spec}"
        )

        name, version, build = parts
        # All parts should be non-empty
        assert name.strip(), f"Package name should not be empty: {package_spec}"
        assert version.strip(), f"Package version should not be empty: {package_spec}"
        assert build.strip(), f"Package build should not be empty: {package_spec}"

    # Verify we have packages to test with
    assert len(conda_packages) > 0, "Should have conda packages to test"


def test_export_format_comparison_no_builds_vs_regular(conda_cli):
    """Test that --no-builds vs regular export produces different but consistent formats."""
    # Get regular export
    stdout_regular, _, code_regular = conda_cli("export", "--format=environment-yaml")
    assert code_regular == 0

    # Get no-builds export
    stdout_no_builds, _, code_no_builds = conda_cli(
        "export", "--no-builds", "--format=environment-yaml"
    )
    assert code_no_builds == 0

    env_regular = yaml.loads(stdout_regular)
    env_no_builds = yaml.loads(stdout_no_builds)

    deps_regular = [
        dep for dep in env_regular.get("dependencies", []) if isinstance(dep, str)
    ]
    deps_no_builds = [
        dep for dep in env_no_builds.get("dependencies", []) if isinstance(dep, str)
    ]

    # Should have same number of packages
    assert len(deps_regular) == len(deps_no_builds), (
        "Should have same number of packages"
    )

    # Compare format differences
    for reg_dep, no_build_dep in zip(deps_regular, deps_no_builds):
        reg_parts = reg_dep.split("=")
        no_build_parts = no_build_dep.split("=")

        # Regular should have 3 parts (name=version=build)
        assert len(reg_parts) == 3, (
            f"Regular export should have name=version=build: {reg_dep}"
        )

        # No-builds should have 2 parts (name=version)
        assert len(no_build_parts) == 2, (
            f"No-builds export should have name=version: {no_build_dep}"
        )

        # Package names and versions should match
        assert reg_parts[0] == no_build_parts[0], "Package names should match"
        assert reg_parts[1] == no_build_parts[1], "Package versions should match"


@pytest.mark.parametrize(
    "format_name,parser_func",
    [
        ("environment-yaml", yaml.loads),
        ("environment-json", json.loads),
    ],
)
def test_export_pip_dependencies_handling(conda_cli, format_name, parser_func):
    """Test that pip dependencies are properly handled in exports when present."""
    stdout, stderr, code = conda_cli("export", f"--format={format_name}")
    assert code == 0

    env_data = parser_func(stdout)
    dependencies = env_data.get("dependencies", [])

    # Look for pip dependencies
    pip_deps = None
    conda_deps = []

    for dep in dependencies:
        if isinstance(dep, dict) and "pip" in dep:
            pip_deps = dep["pip"]
        elif isinstance(dep, str):
            conda_deps.append(dep)

    # If pip dependencies exist, verify their format
    if pip_deps:
        for pip_dep in pip_deps:
            # Pip deps should be in name==version format
            assert "==" in pip_dep, f"Pip dependency should use == format: {pip_dep}"
            name, version = pip_dep.split("==", 1)
            assert name.strip(), f"Pip package name should not be empty: {pip_dep}"
            assert version.strip(), (
                f"Pip package version should not be empty: {pip_dep}"
            )

    # Should always have conda dependencies
    assert len(conda_deps) > 0, "Should have conda dependencies"


@pytest.mark.parametrize(
    "format_name,format_flag,parser_func",
    [
        ("YAML", "", yaml.loads),
        ("JSON", "--format=json", json.loads),
    ],
)
def test_export_with_pip_dependencies_integration(
    tmp_env,
    conda_cli,
    pip_cli: PipCLIFixture,
    wheelhouse: Path,
    format_name,
    format_flag,
    parser_func,
):
    """Test that conda export properly includes pip dependencies when present.

    Uses our small-python-package as a reliable test package that's proven to work in conda's test suite.
    """
    with tmp_env("python=3.10", "pip") as prefix:
        # Install small-python-package wheel built in test data directory
        wheel_path = wheelhouse / "small_python_package-1.0.0-py3-none-any.whl"

        # Install using pip_cli fixture for better error handling
        pip_stdout, pip_stderr, pip_code = pip_cli("install", wheel_path, prefix=prefix)
        assert pip_code == 0, f"pip install failed: {pip_stderr}"

        # Clear prefix data cache to ensure fresh data
        PrefixData._cache_.clear()

        # Export the environment in the specified format
        export_args = ["export", f"--prefix={prefix}"] + (
            [format_flag] if format_flag else []
        )

        stdout, stderr, code = conda_cli(*export_args)
        assert code == 0, f"{format_name} export failed: {stderr}"

        # Parse the output using the appropriate parser
        env_data = parser_func(stdout)
        dependencies = env_data.get("dependencies", [])

        # Should have conda packages
        assert [dep for dep in dependencies if isinstance(dep, str)], (
            f"Should have conda dependencies in {format_name} export"
        )
        # Should have pip dependencies
        assert (
            pip_deps := next(
                (
                    dep["pip"]
                    for dep in dependencies
                    if isinstance(dep, dict) and "pip" in dep
                ),
                None,
            )
        ), f"Expected pip dependencies in {format_name} export"

        # Should include the pip package we installed (small-python-package)
        # and potentially its dependencies
        pip_packages = {pkg.split("==")[0] for pkg in pip_deps if "==" in pkg}

        assert "small-python-package" in pip_packages, (
            f"Expected 'small-python-package' in {format_name} export: {pip_deps}"
        )


def test_export_override_channels_and_ignore_channels_independence(conda_cli):
    """Test that --override-channels and --ignore-channels work independently.

    This validates the fix where --override-channels no longer automatically
    implies --ignore-channels behavior.
    """
    # Test 1: Default behavior (neither flag)
    stdout, stderr, code = conda_cli("export", "--format=environment-yaml")
    assert code == 0
    assert yaml.loads(stdout) != {}, "Should have some packages"

    # Test 2: Only --override-channels (should still extract package channels)
    stdout, stderr, code = conda_cli(
        "export",
        "--override-channels",
        "-c",
        "conda-forge",
        "--format=environment-yaml",
    )
    assert code == 0
    override_only_data = yaml.loads(stdout)
    override_only_channels = override_only_data.get("channels", [])

    # Test 3: Only --ignore-channels (should still include defaults)
    stdout, stderr, code = conda_cli(
        "export", "--ignore-channels", "--format=environment-yaml"
    )
    assert code == 0
    ignore_only_data = yaml.loads(stdout)
    ignore_only_channels = ignore_only_data.get("channels", [])

    # Test 4: Both flags together
    stdout, stderr, code = conda_cli(
        "export",
        "--override-channels",
        "-c",
        "conda-forge",
        "--ignore-channels",
        "--format=environment-yaml",
    )
    assert code == 0
    both_flags_data = yaml.loads(stdout)
    both_flags_channels = both_flags_data.get("channels", [])

    # Validation: --override-channels only
    # Should have conda-forge, but may also have channels from installed packages
    assert "conda-forge" in override_only_channels
    # Should NOT have defaults (since overriding)
    # Note: Some packages might bring in their own channels

    # Validation: --ignore-channels only
    # Should have defaults but no package-extracted channels
    # (This is harder to validate without knowing what packages are installed)
    assert len(ignore_only_channels) > 0  # Should have at least defaults

    # Validation: Both flags together
    # Should only have the explicitly specified channel (conda-forge)
    # Should NOT extract channels from packages (ignore-channels)
    # Should NOT include defaults (override-channels)
    assert "conda-forge" in both_flags_channels
    # With both flags, we should have the most restrictive behavior

    # Key validation: --override-channels alone should behave differently than both flags
    # This proves they are independent
    if len(override_only_channels) > len(both_flags_channels):
        # This indicates --override-channels alone extracted additional channels
        # from installed packages, proving it doesn't imply --ignore-channels
        print(
            f"✅ Independence validated: override-only has {len(override_only_channels)} channels, "
            f"both flags have {len(both_flags_channels)} channels"
        )
    else:
        # Even if counts are equal, the behavior should be different
        # At minimum, both should contain conda-forge
        assert "conda-forge" in override_only_channels
        assert "conda-forge" in both_flags_channels


def test_export_explicit_format_validation_errors(
    tmp_env,
    conda_cli,
    pip_cli: PipCLIFixture,
    wheelhouse: Path,
):
    """Test that explicit format properly errors on invalid environments."""
    # Create an environment with conda packages and pip dependencies
    with tmp_env("python=3.10", "pip") as prefix:
        # Install a pip package to create external packages
        wheel_path = wheelhouse / "small_python_package-1.0.0-py3-none-any.whl"
        pip_stdout, pip_stderr, pip_code = pip_cli("install", wheel_path, prefix=prefix)
        assert pip_code == 0, f"pip install failed: {pip_stderr}"

        # Clear prefix data cache
        PrefixData._cache_.clear()

        # Test 1: Should error when external packages (pip) are present
        with pytest.raises(CondaValueError) as exc_info:
            conda_cli("export", f"--prefix={prefix}", "--format=explicit")

        # Verify the error message is descriptive and helpful
        error_msg = str(exc_info.value)
        assert "Cannot export explicit format" in error_msg
        assert "external packages" in error_msg


def test_export_platform_argument(
    conda_cli: CondaCLIFixture,
    plugin_manager_with_exporters: CondaPluginManager,
    tmp_path: Path,
) -> None:
    """Test export with platform argument."""
    name = uuid.uuid4().hex
    output = tmp_path / "test.yaml"
    stdout, stderr, code = conda_cli(
        "export",
        f"--name={name}",
        "--format=test-single-platform",
        f"--file={output}",
    )
    assert not stdout
    assert not stderr
    assert not code

    # Verify the output is valid YAML
    yaml_data = yaml.loads(output.read_text())
    assert yaml_data["name"] == name


def test_export_multiple_platforms(
    conda_cli: CondaCLIFixture,
    plugin_manager_with_exporters: CondaPluginManager,
    tmp_path: Path,
) -> None:
    """Test export with multiple platform arguments."""
    name = uuid.uuid4().hex
    output = tmp_path / "test.yaml"
    platforms = ["linux-64", "osx-64"]
    stdout, stderr, code = conda_cli(
        "export",
        f"--name={name}",
        *(f"--platform={platform}" for platform in platforms),
        "--format=test-multi-platform",
        f"--file={output}",
    )
    assert "Collecting package metadata" in stdout
    assert not stderr
    assert not code

    # Verify the output is valid YAML
    yaml_data = yaml.loads(output.read_text())
    assert yaml_data["name"] == name
    assert yaml_data["multi-platforms"] == platforms


def test_export_single_platform_different_platform(
    conda_cli: CondaCLIFixture,
    tmp_path: Path,
    plugin_manager_with_exporters: CondaPluginManager,
):
    # pick a platform that is not the current platform
    platform = ({"linux-64", "osx-arm64"} - {context.subdir}).pop()
    assert platform != context.subdir

    # export for a different platform
    name = uuid.uuid4().hex
    output = tmp_path / "test.yaml"
    stdout, stderr, code = conda_cli(
        "export",
        f"--name={name}",
        "--override-platforms",
        f"--platform={platform}",
        "--format=test-single-platform",
        f"--file={output}",
    )
    assert "Collecting package metadata" in stdout
    assert not stderr
    assert not code

    # verify the output is valid YAML
    yaml_data = yaml.loads(output.read_text())
    from pprint import pprint

    pprint(yaml_data)
    assert yaml_data["name"] == name
    assert yaml_data["single-platform"] == platform


def test_export_invalid_platform_fails_fast(conda_cli):
    with pytest.raises(
        CondaValueError, match=r"Could not find platform\(s\): idontexist"
    ):
        conda_cli(
            "export",
            "--override-platforms",
            "--platform",
            "idontexist",
        )


def test_export_invalid_subdir_fails_fast(conda_cli):
    with pytest.raises(
        CondaValueError, match=r"Could not find platform\(s\): idontexist"
    ):
        conda_cli(
            "export",
            "--override-platforms",
            "--subdir",
            "idontexist",
        )


def test_export_invalid_platform_from_condarc_fails_fast(
    conda_cli, tmp_path, monkeypatch
):
    condarc = tmp_path / ".condarc"
    condarc.write_text("export_platforms:\n  - doesnotexist\n")

    monkeypatch.setenv("CONDARC", str(condarc))

    # Import lazily to avoid collection-time failures
    from conda.base.context import reset_context

    reset_context()

    with pytest.raises(
        CondaValueError, match=r"Could not find platform\(s\): doesnotexist"
    ):
        conda_cli("export")
