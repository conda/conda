"""
Replacements for parts of the toolz library.
"""

import itertools
import collections


def groupby_to_dict(keyfunc, sequence):
    """
    toolz-style groupby, returns a dictionary of { key: [group] } instead of
    iterators.
    """
    result = collections.defaultdict(list)
    for key, group in itertools.groupby(sequence, keyfunc):
        result[key].extend(group)
    return dict(result)
