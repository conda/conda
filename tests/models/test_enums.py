# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for conda.models.enums module."""

import pytest

from conda.exceptions import CondaUpgradeError
from conda.models.enums import NoarchType


@pytest.mark.parametrize(
    "value,expected",
    [
        # NoarchType instances should return themselves
        (NoarchType.python, NoarchType.python),
        (NoarchType.generic, NoarchType.generic),
    ],
)
def test_noarch_type_coerce_with_instance(value, expected):
    """Test that coerce returns the same instance when given a NoarchType."""
    assert NoarchType.coerce(value) == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        # Boolean values
        (True, NoarchType.generic),
        (False, None),
    ],
)
def test_noarch_type_coerce_with_bool(value, expected):
    """Test that coerce handles boolean values correctly."""
    assert NoarchType.coerce(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "python",
        "Python",
        "PYTHON",
    ],
)
def test_noarch_type_coerce_with_python_string(value):
    """Test that coerce returns python for 'python' strings (case-insensitive)."""
    assert NoarchType.coerce(value) == NoarchType.python


@pytest.mark.parametrize(
    "value",
    [
        "generic",
        "Generic",
        "GENERIC",
    ],
)
def test_noarch_type_coerce_with_generic_string(value):
    """Test that coerce returns generic for 'generic' strings (case-insensitive)."""
    assert NoarchType.coerce(value) == NoarchType.generic


@pytest.mark.parametrize(
    "value",
    [
        # This is the fix for PR #14179 - handling 'null' values from malformed repodata
        "null",
        "NULL",
        "Null",
        # Other null-like values
        "none",
        "None",
        "NONE",
        # YAML null representation
        "~",
        # Null byte
        "\0",
        # Empty string
        "",
    ],
)
def test_noarch_type_coerce_with_null_values(value):
    """Test that coerce returns None for null-like strings."""
    assert NoarchType.coerce(value) is None


@pytest.mark.parametrize(
    "value",
    [
        "true",
        "True",
        "TRUE",
        "yes",
        "Yes",
        "YES",
        "on",
        "On",
        "ON",
        "y",
        "Y",
        "1",
        "42",
        "1.0",
    ],
)
def test_noarch_type_coerce_with_truthy_strings(value):
    """Test that coerce returns generic for truthy strings and numeric values."""
    assert NoarchType.coerce(value) == NoarchType.generic


@pytest.mark.parametrize(
    "value",
    [
        "false",
        "False",
        "FALSE",
        "off",
        "Off",
        "OFF",
        "no",
        "No",
        "NO",
        "n",
        "N",
        "non",
        "Non",
        "0",
        "0.0",
    ],
)
def test_noarch_type_coerce_with_falsy_strings(value):
    """Test that coerce returns None for falsy strings and zero values."""
    assert NoarchType.coerce(value) is None


@pytest.mark.parametrize(
    "value",
    [
        "invalid",
        "foobar",
        "unknown",
        "other",
    ],
)
def test_noarch_type_coerce_with_invalid_string_raises_error(value):
    """Test that coerce raises CondaUpgradeError for invalid strings."""
    with pytest.raises(
        CondaUpgradeError,
        match=f"The noarch type for this package is set to '{value}'",
    ):
        NoarchType.coerce(value)


def test_noarch_type_coerce_with_object_with_type_attribute():
    """Test that coerce extracts type attribute from objects."""

    class ObjectWithType:
        def __init__(self, noarch_type):
            self.type = noarch_type

    obj_python = ObjectWithType(NoarchType.python)
    assert NoarchType.coerce(obj_python) == NoarchType.python

    obj_generic = ObjectWithType(NoarchType.generic)
    assert NoarchType.coerce(obj_generic) == NoarchType.generic

