# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from .._vendor.auxlib.collection import frozendict

EMPTY_MAP = frozendict()


class _Null(object):
    def __nonzero__(self):
        return False

    def __bool__(self):
        return False

    def __len__(self):
        return 0


# Use this NULL object when needing to distinguish a value from None
# For example, when parsing json, you may need to determine if a json key was given and set
#   to null, or the key didn't exist at all.  There could be a bit of potential confusion here,
#   because in python null == None, while here I'm defining NULL to mean 'not defined'.
NULL = _Null()
