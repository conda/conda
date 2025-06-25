# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for explicit environment handling."""

import pytest

from conda.env.env import Environment
from conda.env.specs.explicit import ExplicitSpec
from tests.env import support_file


@pytest.fixture
def explicit_urls():
    """Fixture providing sample explicit package URLs."""
    return [
        "@EXPLICIT",
        "https://repo.anaconda.com/pkgs/main/linux-64/python-3.9.0-h2a148a8_4.tar.bz2",
        "https://repo.anaconda.com/pkgs/main/linux-64/numpy-1.19.2-py39h89c1606_0.tar.bz2",
    ]


@pytest.fixture
def explicit_environment(explicit_urls):
    """Create an Environment instance for explicit testing."""
    return Environment(
        name="test-explicit",
        dependencies=explicit_urls,
        filename="/path/to/explicit.txt",
    )


def test_environment_with_explicit_dependencies():
    """Test that regular Environment can handle explicit dependencies."""
    urls = [
        "@EXPLICIT",
        "https://repo.anaconda.com/pkgs/main/linux-64/python-3.9.0-h2a148a8_4.tar.bz2",
    ]
    env = Environment(dependencies=urls)

    # Should detect as explicit
    assert env.dependencies.explicit is True


def test_explicit_environment_initialization(explicit_environment):
    """Test Environment initialization with explicit parameters."""
    env = explicit_environment

    # Check basic properties
    assert env.name == "test-explicit"
    assert env.filename == "/path/to/explicit.txt"

    # Check explicit detection
    assert env.dependencies.explicit is True

    # Check dependencies include @EXPLICIT marker
    assert "@EXPLICIT" in env.dependencies.raw


def test_explicit_spec_returns_environment():
    """Test that ExplicitSpec returns regular Environment."""
    explicit_file = support_file("explicit.txt")
    spec = ExplicitSpec(filename=explicit_file)

    env = spec.environment

    # Should be regular Environment, not special subclass
    assert type(env) is Environment
    assert env.dependencies.explicit is True


def test_explicit_environment_for_cep23_compliance(explicit_environment):
    """Test that explicit environments follow CEP-23 by being marked as explicit."""
    env = explicit_environment

    # The environment should be marked as explicit for solver bypass
    assert env.dependencies.explicit is True

    # Dependencies should contain the explicit marker
    raw_deps = env.dependencies.raw or []
    assert "@EXPLICIT" in raw_deps
