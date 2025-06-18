# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for Environment class with explicit functionality."""

import pytest

from conda.env.env import Environment
from conda.env.specs.requirements import RequirementsSpec
from tests.env import support_file


@pytest.fixture(scope="module")
def support_explicit_file():
    """Path to the explicit environment file in the test support directory"""
    return support_file("explicit.txt")


@pytest.fixture(scope="module")
def explicit_urls():
    """Sample URLs for testing explicit environments."""
    return [
        "https://conda.anaconda.org/conda-forge/linux-64/numpy-1.21.5-py39h2a9ead8_0.tar.bz2",
        "https://conda.anaconda.org/conda-forge/linux-64/python-3.9.10-h85951f9_5_cpython.tar.bz2",
    ]


def test_explicit_environment_detection():
    """Test that Environment correctly detects explicit vs regular dependencies."""
    explicit_env = Environment(dependencies=["@EXPLICIT", "test-package"])
    regular_env = Environment(dependencies=["numpy", "pandas"])

    assert explicit_env.dependencies.explicit
    assert not regular_env.dependencies.explicit


def test_explicit_environment_initialization(explicit_urls: list[str]) -> None:
    """Test Environment initialization with explicit parameters."""
    explicit_deps = ["@EXPLICIT"] + explicit_urls
    expected_name = "test-env"
    expected_filename = "/path/to/test.txt"

    env = Environment(
        name=expected_name,
        dependencies=explicit_deps,
        filename=expected_filename,
    )

    assert env.name == expected_name
    assert env.filename == expected_filename
    assert env.dependencies.explicit
    assert env.dependencies.raw == explicit_deps
    assert len(env.dependencies.raw or []) == 3  # Handle potential None


@pytest.mark.parametrize(
    "deps_arrangement",
    [
        # @EXPLICIT at start
        lambda urls: ["@EXPLICIT"] + urls,
        # @EXPLICIT in middle
        lambda urls: urls[:1] + ["@EXPLICIT"] + urls[1:],
        # @EXPLICIT at end
        lambda urls: urls + ["@EXPLICIT"],
    ],
    ids=["explicit_at_start", "explicit_in_middle", "explicit_at_end"],
)
def test_explicit_marker_position(explicit_urls: list[str], deps_arrangement) -> None:
    """Test that @EXPLICIT marker works regardless of position in dependencies."""
    dependencies = deps_arrangement(explicit_urls)

    env = Environment(
        name="test-explicit-position",
        dependencies=dependencies,
        filename="/path/to/explicit-file.txt",
    )

    assert env.dependencies.explicit
    assert "@EXPLICIT" in (env.dependencies.raw or [])
    assert len(env.dependencies.raw or []) == 3  # @EXPLICIT + 2 URLs


def test_requirements_spec_creates_explicit_environment(
    support_explicit_file: str,
) -> None:
    """Test that RequirementsSpec correctly creates explicit Environment instances."""
    spec = RequirementsSpec(filename=support_explicit_file)
    env = spec.environment

    assert isinstance(env, Environment)
    assert env.dependencies.explicit
    assert env.filename == support_explicit_file
    assert len(env.dependencies.raw or []) == 3  # @EXPLICIT + 2 package URLs


def test_explicit_environment_cep23_compliance(explicit_urls: list[str]) -> None:
    """Test that explicit Environment follows CEP-23 requirements."""
    explicit_deps = ["@EXPLICIT"] + explicit_urls

    env = Environment(
        name="test-cep23",
        dependencies=explicit_deps,
        filename="/path/to/explicit-file.txt",
    )

    assert env.dependencies is not None
    assert env.dependencies.explicit
    assert "@EXPLICIT" in (env.dependencies.raw or [])
    assert env.filename is not None
