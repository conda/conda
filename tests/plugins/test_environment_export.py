# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for environment export functionality."""

from __future__ import annotations

import json
from contextlib import nullcontext
from typing import TYPE_CHECKING

import pytest
import yaml

from conda.common.serialize import yaml as yaml_serializer
from conda.exceptions import (
    CondaValueError,
    EnvironmentExporterNotDetected,
    PluginError,
)
from conda.models.channel import Channel
from conda.models.environment import Environment
from conda.models.match_spec import MatchSpec
from conda.models.records import PackageRecord
from conda.plugins.environment_exporters.environment_yml import (
    ENVIRONMENT_JSON_FORMAT,
    ENVIRONMENT_YAML_FORMAT,
)
from conda.plugins.environment_exporters.explicit import EXPLICIT_FORMAT
from conda.plugins.environment_exporters.requirements_txt import REQUIREMENTS_FORMAT
from conda.plugins.types import CondaEnvironmentExporter

from ..conftest import Exporters

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from pathlib import Path
    from typing import Any

    from conda.tests.fixtures import CondaCliFixture, TmpEnvFixture
    from pytest import FixtureRequest

    from conda.plugins.manager import CondaPluginManager


@pytest.fixture
def test_env() -> Environment:
    """Create a test environment for exporter testing."""
    return Environment(
        name="test-env",
        prefix="/tmp/test-env",
        platform="linux-64",
        requested_packages=[MatchSpec("python=3.9"), MatchSpec("numpy")],
    )


@pytest.fixture
def test_env_with_explicit_packages():
    """Create a test environment with explicit packages (URLs) for explicit exporter testing."""
    # Create mock PackageRecord objects with proper URLs
    python_pkg = PackageRecord(
        name="python",
        version="3.9.7",
        build="h12debd9_0",
        build_number=0,
        channel=Channel("https://repo.anaconda.com/pkgs/main"),
        subdir="linux-64",
        fn="python-3.9.7-h12debd9_0.conda",
        url="https://repo.anaconda.com/pkgs/main/linux-64/python-3.9.7-h12debd9_0.conda",
    )

    numpy_pkg = PackageRecord(
        name="numpy",
        version="1.21.0",
        build="py39hdbf815f_0",
        build_number=0,
        channel=Channel("https://repo.anaconda.com/pkgs/main"),
        subdir="linux-64",
        fn="numpy-1.21.0-py39hdbf815f_0.conda",
        url="https://repo.anaconda.com/pkgs/main/linux-64/numpy-1.21.0-py39hdbf815f_0.conda",
    )

    return Environment(
        name="test-env",
        prefix="/tmp/test-env",
        platform="linux-64",
        explicit_packages=[python_pkg, numpy_pkg],
    )


@pytest.mark.parametrize(
    "format_name,parser_func",
    [
        (ENVIRONMENT_YAML_FORMAT, yaml.safe_load),
        (ENVIRONMENT_JSON_FORMAT, json.loads),
    ],
)
def test_builtin_structured_exporters(
    plugin_manager_with_exporters: CondaPluginManager,
    test_env: Environment,
    format_name: str,
    parser_func: Callable[[str], Any],
):
    """Test built-in exporters that produce structured output (YAML/JSON)."""
    # Test that exporter is available
    exporter = plugin_manager_with_exporters.get_environment_exporter_by_format(
        format_name
    )
    assert exporter is not None
    assert exporter.name == format_name

    # Test export functionality
    result = exporter.export(test_env)

    # Parse using appropriate parser
    parsed = parser_func(result)

    # Verify structure
    assert parsed["name"] == "test-env"
    assert "dependencies" in parsed
    assert len(parsed["dependencies"]) >= 2

    # Verify test packages are present
    deps_str = str(parsed["dependencies"])
    assert "python" in deps_str
    assert "numpy" in deps_str


def test_yaml_exporter_explicit_packages_format(
    plugin_manager_with_exporters: CondaPluginManager,
    test_env_with_explicit_packages: Environment,
):
    """Test that YAML exporter produces correct dependency format with explicit packages.

    This test validates that both normal and fallback cases produce the single equals
    format (name=version=build) that matches production conda behavior.
    """
    exporter = plugin_manager_with_exporters.get_environment_exporter_by_format(
        ENVIRONMENT_YAML_FORMAT
    )

    # Export the environment
    result = exporter.export(test_env_with_explicit_packages)
    parsed = yaml.safe_load(result)

    # Verify dependencies use correct format: name=version=build (single equals throughout)
    dependencies = parsed["dependencies"]
    assert len(dependencies) == 2

    # Check specific packages and format
    dep_strs = set(dependencies)
    assert "python=3.9.7=h12debd9_0" in dep_strs  # Single equals throughout
    assert "numpy=1.21.0=py39hdbf815f_0" in dep_strs  # Single equals throughout

    # Verify correct single-equals format is used (matches production conda)
    for dep in dependencies:
        # Count equals signs: should be 2 total (name=version=build)
        equals_count = dep.count("=")
        assert equals_count == 2, (
            f"Dependency '{dep}' should have 2 equals signs (name=version=build)"
        )

        # Verify no double equals (should be single equals throughout)
        assert "==" not in dep, (
            f"Dependency '{dep}' should not contain '==' (should be single = throughout)"
        )


def test_explicit_exporter_cep23_compliance_error(
    plugin_manager_with_exporters: CondaPluginManager,
):
    """Test that explicit exporter raises error for packages without URLs (CEP 23 compliance)."""
    from conda.exceptions import CondaValueError
    from conda.models.environment import Environment
    from conda.models.records import PackageRecord

    # Create package without URL or proper channel info (violates CEP 23)
    minimal_pkg = PackageRecord(
        name="test-package",
        version="1.0.0",
        build="py39_0",
        build_number=0,
        # No URL, no channel, no fn - cannot construct URL
    )

    env = Environment(
        name="test-env",
        prefix="/tmp/test-env",
        platform="linux-64",
        explicit_packages=[minimal_pkg],
    )

    exporter = plugin_manager_with_exporters.get_environment_exporter_by_format(
        EXPLICIT_FORMAT
    )

    # Should raise error instead of falling back to spec format
    with pytest.raises(CondaValueError, match="explicit format requires package URLs"):
        exporter.export(env)


def test_builtin_requirements_exporter(
    plugin_manager_with_exporters: CondaPluginManager,
    test_env: Environment,
):
    """Test the built-in requirements environment exporter with requested packages."""
    # Test that exporter is available
    exporter_config = plugin_manager_with_exporters.get_environment_exporter_by_format(
        REQUIREMENTS_FORMAT
    )
    assert exporter_config is not None
    assert exporter_config.name == REQUIREMENTS_FORMAT

    # Test export functionality with requested packages (should create requirements file)
    result = exporter_config.export(test_env)

    # Verify it's NOT an @EXPLICIT format (CEP 23 compliance)
    assert "@EXPLICIT" not in result

    # Verify it's a requirements file with MatchSpec strings
    assert "# Note: This is a conda requirements file (MatchSpec format)" in result
    assert "# Contains conda package specifications, not pip requirements" in result

    # Verify platform information is included
    assert f"# platform: {test_env.platform}" in result

    # Check that MatchSpec strings are preserved (not converted)
    lines = result.split("\n")
    package_specs = [line for line in lines if line and not line.startswith("#")]

    # Should have 2 package specifications
    assert len(package_specs) == 2

    # Check the MatchSpec format (should use original MatchSpec string representation)
    specs_text = "\n".join(package_specs)
    assert "python" in specs_text
    assert "numpy" in specs_text


def test_builtin_explicit_exporter_with_urls(
    plugin_manager_with_exporters: CondaPluginManager,
    test_env_with_explicit_packages: Environment,
):
    """Test the built-in explicit environment exporter with actual package URLs."""
    # Test that exporter is available
    exporter_config = plugin_manager_with_exporters.get_environment_exporter_by_format(
        EXPLICIT_FORMAT
    )
    assert exporter_config is not None

    # Test export functionality with explicit packages (should create true explicit file)
    result = exporter_config.export(test_env_with_explicit_packages)

    # Verify it IS an @EXPLICIT format (CEP 23 compliance)
    assert "@EXPLICIT" in result

    # Verify platform information is included
    assert f"# platform: {test_env_with_explicit_packages.platform}" in result

    # Check that URLs are included
    lines = result.split("\n")
    url_lines = [line for line in lines if line.startswith("https://")]

    # Should have URLs for both packages
    assert len(url_lines) == 2
    assert "python-3.9.7-h12debd9_0.conda" in result
    assert "numpy-1.21.0-py39hdbf815f_0.conda" in result


@pytest.mark.parametrize(
    "format_name,test_env_fixture,expected_error_fragment",
    [
        (EXPLICIT_FORMAT, "test_env", "Cannot export explicit format"),
        (
            REQUIREMENTS_FORMAT,
            "test_env_with_explicit_packages",
            "Cannot export requirements format",
        ),
    ],
)
def test_exporter_error_conditions(
    plugin_manager_with_exporters: CondaPluginManager,
    request: FixtureRequest,
    format_name: str,
    test_env_fixture: str,
    expected_error_fragment,
):
    """Test exporters fail appropriately with incompatible environment data."""
    # Get the test environment from fixture name
    test_env = request.getfixturevalue(test_env_fixture)

    # Get exporter
    exporter = plugin_manager_with_exporters.get_environment_exporter_by_format(
        format_name
    )
    assert exporter is not None

    # Test export should fail with appropriate error
    with pytest.raises(CondaValueError, match=expected_error_fragment):
        exporter.export(test_env)


def test_get_environment_exporters(plugin_manager_with_exporters: CondaPluginManager):
    """Test getting environment exporters mapping."""
    assert {
        exporter.name
        for exporter in plugin_manager_with_exporters.get_environment_exporters()
    } == {
        ENVIRONMENT_YAML_FORMAT,
        ENVIRONMENT_JSON_FORMAT,
        EXPLICIT_FORMAT,
        REQUIREMENTS_FORMAT,
        "test-single-platform",
        "test-multi-platform",
    }


@pytest.mark.parametrize(
    "filename,expected_format",
    [
        ("environment.yaml", ENVIRONMENT_YAML_FORMAT),
        ("environment.yml", ENVIRONMENT_YAML_FORMAT),
        ("environment.json", ENVIRONMENT_JSON_FORMAT),
        ("explicit.txt", EXPLICIT_FORMAT),
        ("requirements.txt", REQUIREMENTS_FORMAT),
        ("spec.txt", REQUIREMENTS_FORMAT),
        ("my-env.yaml", None),  # Not a recognized default filename
        ("env.unknown", None),
    ],
)
def test_detect_environment_exporter(
    plugin_manager_with_exporters: CondaPluginManager,
    filename: str,
    expected_format: str | None,
):
    """Test detecting exporter by exact filename matching."""
    if expected_format is None:
        # Should raise exception for unrecognized filenames
        with pytest.raises(EnvironmentExporterNotDetected):
            plugin_manager_with_exporters.detect_environment_exporter(filename)
    else:
        exporter = plugin_manager_with_exporters.detect_environment_exporter(filename)
        assert exporter is not None
        assert exporter.name == expected_format


@pytest.mark.parametrize(
    "format_name,should_exist",
    [
        (ENVIRONMENT_YAML_FORMAT, True),
        ("yaml", True),  # alias
        ("yml", True),  # alias
        (ENVIRONMENT_JSON_FORMAT, True),
        ("json", True),  # alias
        (EXPLICIT_FORMAT, True),
        (REQUIREMENTS_FORMAT, True),
        ("txt", True),  # alias
        ("reqs", True),  # alias
        ("unknown", False),
    ],
)
def test_get_environment_exporter_by_format(
    plugin_manager_with_exporters: CondaPluginManager,
    format_name: str,
    should_exist: bool,
):
    """Test getting exporter by format name including aliases."""
    if should_exist:
        exporter = plugin_manager_with_exporters.get_environment_exporter_by_format(
            format_name
        )
        assert exporter is not None
        # For aliases, verify that an exporter was found and has a valid canonical name
        assert exporter.name is not None
        assert len(exporter.name) > 0

        # If format_name is an alias, verify it actually resolves to the exporter
        is_alias = format_name in exporter.aliases
        is_canonical = format_name == exporter.name
        assert is_alias or is_canonical, (
            f"Format '{format_name}' should be either canonical name or alias"
        )
    else:
        # Should raise CondaValueError for unknown formats
        with pytest.raises(
            CondaValueError, match=f"Unknown export format '{format_name}'"
        ):
            plugin_manager_with_exporters.get_environment_exporter_by_format(
                format_name
            )


def test_yaml_exporter_handles_missing_name(
    plugin_manager_with_exporters: CondaPluginManager,
):
    """Test YAML exporter handles case where environment has no name."""
    exporter_config = plugin_manager_with_exporters.get_environment_exporter_by_format(
        ENVIRONMENT_YAML_FORMAT
    )
    assert exporter_config is not None

    # Create environment without name
    env = Environment(
        name=None,  # No name
        prefix="/tmp/test-env",
        platform="linux-64",
        requested_packages=[MatchSpec("python")],
    )

    # Export should still work
    result = exporter_config.export(env)

    # Parse YAML to verify structure instead of checking string format
    parsed = yaml.safe_load(result)

    # Should have a name field (even if None/null)
    assert "name" in parsed


@pytest.mark.parametrize(
    "format_name,expected_aliases",
    [
        (ENVIRONMENT_YAML_FORMAT, ("yaml", "yml")),
        (ENVIRONMENT_JSON_FORMAT, ("json",)),
        (EXPLICIT_FORMAT, ()),
        (REQUIREMENTS_FORMAT, ("reqs", "txt")),
    ],
)
def test_builtin_exporters_define_expected_aliases(
    plugin_manager_with_exporters: CondaPluginManager,
    format_name: str,
    expected_aliases: tuple[str, ...],
):
    """Test that built-in exporters define their expected aliases."""
    exporter = plugin_manager_with_exporters.get_environment_exporter_by_format(
        format_name
    )
    assert exporter is not None

    # Check that all expected aliases are present
    for alias in expected_aliases:
        assert alias in exporter.aliases

    # Verify alias resolution works - each alias should resolve back to this exporter
    for alias in expected_aliases:
        alias_resolved = (
            plugin_manager_with_exporters.get_environment_exporter_by_format(alias)
        )
        assert alias_resolved.name == exporter.name


def test_alias_normalization_and_collision_detection():
    """Test that aliases are normalized and collision detection works."""
    # Test alias normalization (mixed case, whitespace, and duplicates)
    exporter = CondaEnvironmentExporter(
        name="test-exporter",
        aliases=(" YAML ", "YML", "yml", "  json  "),
        default_filenames=("test.yaml",),
        export=lambda env: "test",
    )

    # Aliases should be normalized to lowercase and stripped
    assert exporter.aliases == ("yaml", "yml", "json")

    # Test invalid alias type raises error
    with pytest.raises(PluginError, match="Invalid plugin aliases"):
        CondaEnvironmentExporter(
            name="bad-exporter",
            aliases=(123, "valid"),  # Non-string alias
            default_filenames=("test.yaml",),
            export=lambda env: "test",
        )


@pytest.mark.parametrize(
    "args,format",
    [
        (["list", "--explicit"], EXPLICIT_FORMAT),
        (["env", "export"], ENVIRONMENT_YAML_FORMAT),
        # (["list", "--export"], REQUIREMENTS_FORMAT),
    ],
)
def test_compare_export_commands(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCliFixture,
    test_recipes_channel: Path,
    args: list[str],
    format: str,
):
    """Test that the new export commmand produces the same output as the legacy command."""
    with tmp_env("small-executable") as prefix:
        old_output, _, _ = conda_cli(*args, f"--prefix={prefix}")
        new_output, _, _ = conda_cli(
            "export",
            f"--prefix={prefix}",
            f"--format={format}",
        )
        assert old_output == new_output


def test_single_platform_export(
    plugin_manager_with_exporters: CondaPluginManager,
    test_env: Environment,
):
    exporter = plugin_manager_with_exporters.get_environment_exporter_by_format(
        "test-single-platform"
    )
    assert exporter is not None
    assert isinstance(exporter, CondaEnvironmentExporter)
    assert exporter.export == Exporters.single_platform_export
    result = exporter.export(test_env)
    first, text = result.strip().split("\n", 1)
    assert first == "# This is a single-platform export"
    parsed = yaml_serializer.loads(text)
    assert parsed["name"] == test_env.name
    assert parsed["single-platform"] == test_env.platform
    packages = iter(parsed["packages"])
    for match_spec in test_env.requested_packages:
        assert next(packages) == str(match_spec)
    for record in test_env.explicit_packages:
        assert next(packages) == str(record)
    for pkg in test_env.external_packages.get("pip", []):
        assert next(packages) == f"pip::{pkg}"


def test_multi_platform_export(
    plugin_manager_with_exporters: CondaPluginManager,
    test_env: Environment,
):
    exporter = plugin_manager_with_exporters.get_environment_exporter_by_format(
        "test-multi-platform"
    )
    assert exporter is not None
    assert isinstance(exporter, CondaEnvironmentExporter)
    assert exporter.multiplatform_export == Exporters.multi_platform_export
    result = exporter.multiplatform_export([test_env, test_env])
    first, text = result.strip().split("\n", 1)
    assert first == "# This is a multi-platform export"
    parsed = yaml_serializer.loads(text)
    assert parsed["name"] == test_env.name
    assert parsed["multi-platforms"] == [test_env.platform, test_env.platform]
    packages = iter(parsed["packages"])
    for _ in range(2):
        for match_spec in test_env.requested_packages:
            assert next(packages) == str(match_spec)
        for record in test_env.explicit_packages:
            assert next(packages) == str(record)
        for pkg in test_env.external_packages.get("pip", []):
            assert next(packages) == f"pip::{pkg}"


@pytest.mark.parametrize(
    "export, multiplatform_export, raises",
    [
        pytest.param(None, None, True, id="none"),
        pytest.param(lambda env: "test", lambda env, envs: "test", True, id="both"),
        pytest.param(lambda env: "test", None, False, id="export"),
        pytest.param(None, lambda env, envs: "test", False, id="multiplatform_export"),
    ],
)
def test_only_one_export(
    export: Callable[[Environment], str] | None,
    multiplatform_export: Callable[[Environment, Iterable[Environment]], str] | None,
    raises: bool,
):
    with (
        pytest.raises(
            PluginError, match="Exactly one of export or multiplatform_export"
        )
        if raises
        else nullcontext()
    ):
        CondaEnvironmentExporter(
            name="test-exporter",
            aliases=(),
            default_filenames=(),
            export=export,
            multiplatform_export=multiplatform_export,
        )
