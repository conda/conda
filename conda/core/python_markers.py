# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
See distlib:
https://bitbucket.org/pypa/distlib/src/34629e41cdff5c29429c7a4d1569ef5508b56929/distlib/util.py?at=default&fileviewer=file-view-default
https://bitbucket.org/pypa/distlib/src/34629e41cdff5c29429c7a4d1569ef5508b56929/distlib/markers.py?at=default&fileviewer=file-view-default
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import platform
import re
import sys

from ..common.compat import string_types


# See: https://bitbucket.org/pypa/distlib/src/34629e41cdff5c29429c7a4d1569ef5508b56929/distlib/util.py?at=default&fileviewer=file-view-default  # NOQA
# ------------------------------------------------------------------------------------------------
def parse_marker(marker_string):
    """
    Parse marker string and return a dictionary containing a marker expression.

    The dictionary will contain keys "op", "lhs" and "rhs" for non-terminals in
    the expression grammar, or strings. A string contained in quotes is to be
    interpreted as a literal string, and a string not contained in quotes is a
    variable (such as os_name).
    """
    def marker_var(remaining):
        # either identifier, or literal string
        m = IDENTIFIER.match(remaining)
        if m:
            result = m.groups()[0]
            remaining = remaining[m.end():]
        elif not remaining:
            raise SyntaxError('unexpected end of input')
        else:
            q = remaining[0]
            if q not in '\'"':
                raise SyntaxError('invalid expression: %s' % remaining)
            oq = '\'"'.replace(q, '')
            remaining = remaining[1:]
            parts = [q]
            while remaining:
                # either a string chunk, or oq, or q to terminate
                if remaining[0] == q:
                    break
                elif remaining[0] == oq:
                    parts.append(oq)
                    remaining = remaining[1:]
                else:
                    m = STRING_CHUNK.match(remaining)
                    if not m:
                        raise SyntaxError('error in string literal: %s' % remaining)
                    parts.append(m.groups()[0])
                    remaining = remaining[m.end():]
            else:
                s = ''.join(parts)
                raise SyntaxError('unterminated string: %s' % s)
            parts.append(q)
            result = ''.join(parts)
            remaining = remaining[1:].lstrip()  # skip past closing quote
        return result, remaining

    def marker_expr(remaining):
        if remaining and remaining[0] == '(':
            result, remaining = marker(remaining[1:].lstrip())
            if remaining[0] != ')':
                raise SyntaxError('unterminated parenthesis: %s' % remaining)
            remaining = remaining[1:].lstrip()
        else:
            lhs, remaining = marker_var(remaining)
            while remaining:
                m = MARKER_OP.match(remaining)
                if not m:
                    break
                op = m.groups()[0]
                remaining = remaining[m.end():]
                rhs, remaining = marker_var(remaining)
                lhs = {'op': op, 'lhs': lhs, 'rhs': rhs}
            result = lhs
        return result, remaining

    def marker_and(remaining):
        lhs, remaining = marker_expr(remaining)
        while remaining:
            m = AND.match(remaining)
            if not m:
                break
            remaining = remaining[m.end():]
            rhs, remaining = marker_expr(remaining)
            lhs = {'op': 'and', 'lhs': lhs, 'rhs': rhs}
        return lhs, remaining

    def marker(remaining):
        lhs, remaining = marker_and(remaining)
        while remaining:
            m = OR.match(remaining)
            if not m:
                break
            remaining = remaining[m.end():]
            rhs, remaining = marker_and(remaining)
            lhs = {'op': 'or', 'lhs': lhs, 'rhs': rhs}
        return lhs, remaining

    return marker(marker_string)


# See: https://bitbucket.org/pypa/distlib/src/34629e41cdff5c29429c7a4d1569ef5508b56929/distlib/markers.py?at=default&fileviewer=file-view-default  # NOQA
# ------------------------------------------------------------------------------------------------
#
# Requirement parsing code as per PEP 508
#

IDENTIFIER = re.compile(r'^([\w\.-]+)\s*')
VERSION_IDENTIFIER = re.compile(r'^([\w\.*+-]+)\s*')
COMPARE_OP = re.compile(r'^(<=?|>=?|={2,3}|[~!]=)\s*')
MARKER_OP = re.compile(r'^((<=?)|(>=?)|={2,3}|[~!]=|in|not\s+in)\s*')
OR = re.compile(r'^or\b\s*')
AND = re.compile(r'^and\b\s*')
NON_SPACE = re.compile(r'(\S+)\s*')
STRING_CHUNK = re.compile(r'([\s\w\.{}()*+#:;,/?!~`@$%^&=|<>\[\]-]+)')


def _is_literal(o):
    if not isinstance(o, string_types) or not o:
        return False
    return o[0] in '\'"'


class Evaluator(object):
    """
    This class is used to evaluate marker expessions.
    """

    operations = {
        '==': lambda x, y: x == y,
        '===': lambda x, y: x == y,
        '~=': lambda x, y: x == y or x > y,
        '!=': lambda x, y: x != y,
        '<': lambda x, y: x < y,
        '<=': lambda x, y: x == y or x < y,
        '>': lambda x, y: x > y,
        '>=': lambda x, y: x == y or x > y,
        'and': lambda x, y: x and y,
        'or': lambda x, y: x or y,
        'in': lambda x, y: x in y,
        'not in': lambda x, y: x not in y,
    }

    def evaluate(self, expr, context):
        """
        Evaluate a marker expression returned by the :func:`parse_requirement`
        function in the specified context.
        """
        if isinstance(expr, string_types):
            if expr[0] in '\'"':
                result = expr[1:-1]
            else:
                if expr not in context:
                    raise SyntaxError('unknown variable: %s' % expr)
                result = context[expr]
        else:
            assert isinstance(expr, dict)
            op = expr['op']
            if op not in self.operations:
                raise NotImplementedError('op not implemented: %s' % op)
            elhs = expr['lhs']
            erhs = expr['rhs']
            if _is_literal(expr['lhs']) and _is_literal(expr['rhs']):
                raise SyntaxError('invalid comparison: %s %s %s' % (elhs, op, erhs))

            lhs = self.evaluate(elhs, context)
            rhs = self.evaluate(erhs, context)
            result = self.operations[op](lhs, rhs)
        return result


# def update_marker_context(python_version):
#     """Update default marker context to include environment python version."""
#     updated_context = DEFAULT_MARKER_CONTEXT.copy()
#     context = {
#         'python_full_version': python_version,
#         'python_version': '.'.join(python_version.split('.')[:2]),
#         'extra': '',
#     }
#     updated_context.update(context)
#     return updated_context


def get_default_marker_context():
    """Return the default context dictionary to use when parsing markers."""

    def format_full_version(info):
        version = '%s.%s.%s' % (info.major, info.minor, info.micro)
        kind = info.releaselevel
        if kind != 'final':
            version += kind[0] + str(info.serial)
        return version

    if hasattr(sys, 'implementation'):
        implementation_version = format_full_version(sys.implementation.version)
        implementation_name = sys.implementation.name
    else:
        implementation_version = '0'
        implementation_name = ''

    result = {
        # See: https://www.python.org/dev/peps/pep-0508/#environment-markers
        'implementation_name': implementation_name,
        'implementation_version': implementation_version,
        'os_name': os.name,
        'platform_machine': platform.machine(),
        'platform_python_implementation': platform.python_implementation(),
        'platform_release': platform.release(),
        'platform_system': platform.system(),
        'platform_version': platform.version(),
        'python_full_version': platform.python_version(),
        'python_version': '.'.join(platform.python_version().split('.')[:2]),
        'sys_platform': sys.platform,
        # See: https://www.python.org/dev/peps/pep-0345/#environment-markers
        'os.name': os.name,
        'platform.python_implementation': platform.python_implementation(),
        'platform.version': platform.version(),
        'platform.machine': platform.machine(),
        'sys.platform': sys.platform,
        'extra': '',
    }
    return result


DEFAULT_MARKER_CONTEXT = get_default_marker_context()
evaluator = Evaluator()


# FIXME: Should this raise errors, or fail silently or with a warning?
def interpret(marker, execution_context=None):
    """
    Interpret a marker and return a result depending on environment.

    :param marker: The marker to interpret.
    :type marker: str
    :param execution_context: The context used for name lookup.
    :type execution_context: mapping
    """
    try:
        expr, rest = parse_marker(marker)
    except Exception as e:
        raise SyntaxError('Unable to interpret marker syntax: %s: %s' % (marker, e))

    if rest and rest[0] != '#':
        raise SyntaxError('unexpected trailing data in marker: %s: %s' % (marker, rest))

    context = DEFAULT_MARKER_CONTEXT.copy()
    if execution_context:
        context.update(execution_context)

    return evaluator.evaluate(expr, context)
