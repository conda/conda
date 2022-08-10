"""
Indirection to tls / toolz library, just the imports we use.
"""

try:
    from toolz import merge, take, interleave, excepts, merge_with, concatv, concat, drop, accumulate, groupby, unique
except ImportError:
    from conda._vendor.toolz import merge, take, interleave, excepts, merge_with, concatv, concat, drop, accumulate, groupby, unique
