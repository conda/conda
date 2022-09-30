# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

"""
Replacements for parts the toolz library.
"""

import itertools


def groupby_to_dict(keyfunc, sequence):
    """
    toolz-style groupby, returns a dictionary of { key: [group] } instead of
    iterators.
    """
    result = {}
    for key, group in itertools.groupby(sequence, keyfunc):
        value = result.get(key, [])
        value.extend(group)
        result[key] = value
    return result
