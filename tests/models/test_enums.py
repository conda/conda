# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for conda.models.enums module."""

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from conda.exceptions import CondaUpgradeError
from conda.models.enums import NoarchType

if TYPE_CHECKING:
    from typing import Any


@dataclass
class ObjectWithType:
    type: NoarchType


@pytest.mark.parametrize(
    "value,expected",
    [
        # NoarchType instances should return themselves
        (NoarchType.python, NoarchType.python),
        (NoarchType.generic, NoarchType.generic),
        # ObjectWithType
        (ObjectWithType(NoarchType.python), NoarchType.python),
        (ObjectWithType(NoarchType.generic), NoarchType.generic),
        # Boolean
        (True, NoarchType.generic),
        (False, None),
        # Truthy strings
        ("true", NoarchType.generic),
        ("True", NoarchType.generic),
        ("TRUE", NoarchType.generic),
        ("yes", NoarchType.generic),
        ("Yes", NoarchType.generic),
        ("YES", NoarchType.generic),
        ("on", NoarchType.generic),
        ("On", NoarchType.generic),
        ("ON", NoarchType.generic),
        ("y", NoarchType.generic),
        ("Y", NoarchType.generic),
        ("1", NoarchType.generic),
        ("42", NoarchType.generic),
        ("1.0", NoarchType.generic),
        # Falsy strings
        ("false", None),
        ("False", None),
        ("FALSE", None),
        ("off", None),
        ("Off", None),
        ("OFF", None),
        ("no", None),
        ("No", None),
        ("NO", None),
        ("n", None),
        ("N", None),
        ("non", None),
        ("Non", None),
        ("0", None),
        ("0.0", None),
        # Python strings
        ("python", NoarchType.python),
        ("Python", NoarchType.python),
        ("PYTHON", NoarchType.python),
        # Generic strings
        ("generic", NoarchType.generic),
        ("Generic", NoarchType.generic),
        ("GENERIC", NoarchType.generic),
        # This is the fix for PR #14179 - handling 'null' values from malformed repodata
        ("null", None),
        ("NULL", None),
        ("Null", None),
        # Other null-like values
        ("none", None),
        ("None", None),
        ("NONE", None),
        # YAML null representation
        ("~", None),
        # Null byte
        ("\0", None),
        # Empty string
        ("", None),
        # Invalid
        ("invalid", CondaUpgradeError),
        ("foobar", CondaUpgradeError),
        ("unknown", CondaUpgradeError),
        ("other", CondaUpgradeError),
    ],
)
def test_noarch_type_coercion(
    value: Any,
    expected: NoarchType | None | CondaUpgradeError,
):
    """Test that NoarchType.coerce returns the expected value for given input."""
    with (
        pytest.raises(
            CondaUpgradeError,
            match=f"The noarch type for this package is set to '{value}'",
        )
        if expected == CondaUpgradeError
        else nullcontext()
    ):
        assert NoarchType.coerce(value) == expected
