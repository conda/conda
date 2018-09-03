# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for python environment marker evaluation."""
from __future__ import absolute_import, division, print_function, unicode_literals

from conda.core import python_dist as pd
from conda.core import python_markers as pm

import pytest


# Helpers
# -----------------------------------------------------------------------------
def _print_output(*args):
    """Helper function to print output in case of failed tests."""
    for arg in args:
        print(arg)
    print('\n')


# Markers
# -----------------------------------------------------------------------------
def test_evaluate_marker():
    # See: https://www.python.org/dev/peps/pep-0508/#complete-grammar
    # ((marker_expr, context, extras, expected_output), ...)
    test_cases = (
        # Valid context
        ('spam == "1.0"', {'spam': '1.0'}, True),
        # Should parse as (a and b) or c
        ("a=='a' and b=='b' or c=='c'", {'a': 'a', 'b': 'b', 'c': ''}, True),
        # Overriding precedence -> a and (b or c)
        ("a=='a' and (b=='b' or c=='c')", {'a': 'a', 'b': '', 'c': ''}, None),
        # Overriding precedence -> (a or b) and c
        ("(a=='a' or b=='b') and c=='c'", {'a': 'a', 'b': '', 'c': ''}, None),
    )
    for marker_expr, context, expected_output in test_cases:
        output = None
        if expected_output:
            output = pm.interpret(marker_expr, context)
            assert output is expected_output
        else:
            output = pm.interpret(marker_expr, context)
        _print_output(marker_expr, context, output, expected_output)

    # Test cases syntax error
    test_cases = (
        ('spam == "1.0"', {}, None),
        ('spam2 == "1.0"', {'spam': '1.0'}, None),
        # Malformed
        ('spam2 = "1.0"', {'spam': '1.0'}, None),
    )
    for marker_expr, context, expected_output in test_cases:
        output = None
        with pytest.raises(SyntaxError):
            output = pm.interpret(marker_expr, context)


def test_update_marker_context():
    pyver = '2.8.1'
    context = pd.update_marker_context(pyver)
    _print_output(pyver, context)
    assert context['extra'] == ''
    assert context['python_version'] == '.'.join(pyver.split('.')[:2])
    assert context['python_full_version'] == pyver


def test_get_default_marker_context():
    context = pm.get_default_marker_context()
    for key, val in context.items():
        # Check deprecated keys have same value as new keys (. -> _)
        if '.' in key:
            other_val = context.get(key.replace('.', '_'))
            _print_output(val, other_val)
            assert val == other_val
