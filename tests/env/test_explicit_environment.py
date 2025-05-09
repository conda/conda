# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the ExplicitEnvironment class."""

import pytest

from conda.env.env import Environment
from conda.env.explicit import ExplicitEnvironment
from conda.env.specs.requirements import ExplicitRequirementsSpec
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


@pytest.fixture(scope="function")
def explicit_env(explicit_urls):
    """Create an ExplicitEnvironment instance for testing."""
    return ExplicitEnvironment(
        name="test-explicit",
        dependencies=explicit_urls,
        filename="/path/to/explicit-file.txt",
    )


def test_explicit_environment_is_environment_subclass():
    """Test that ExplicitEnvironment is a subclass of Environment."""
    assert issubclass(ExplicitEnvironment, Environment)


def test_explicit_environment_initialization(explicit_urls):
    """Test ExplicitEnvironment initialization with typical parameters."""
    env = ExplicitEnvironment(
        name="test-env", dependencies=explicit_urls, filename="/path/to/test.txt"
    )

    # Check standard Environment properties
    assert env.name == "test-env"
    assert len(env.dependencies.raw) == 2

    # Check ExplicitEnvironment-specific properties
    assert env.explicit_specs == explicit_urls
    assert env.explicit_filename == "/path/to/test.txt"


def test_requirements_spec_returns_explicit_environment(support_explicit_file):
    """Test that ExplicitRequirementsSpec returns an ExplicitEnvironment instance."""
    spec = ExplicitRequirementsSpec(filename=support_explicit_file)
    env = spec.environment

    # Verify it's the right type
    assert isinstance(env, ExplicitEnvironment)

    # Check expected attributes
    assert env.explicit_filename == support_explicit_file
    assert hasattr(env, "explicit_specs")
    assert len(env.explicit_specs) == 2


def test_explicit_environment_for_cep23_compliance(explicit_env):
    """Test that ExplicitEnvironment follows CEP-23 by storing explicit specs separately."""
    # The environment should have both regular dependencies and explicit_specs
    assert explicit_env.dependencies is not None
    assert explicit_env.explicit_specs is not None

    # Dependencies and explicit_specs should match in this test case
    assert len(explicit_env.dependencies.raw) == len(explicit_env.explicit_specs)

    # Explicit filename should be stored
    assert explicit_env.explicit_filename is not None
