# -*- coding: utf-8 -*-
"""
This module is DEPRECATED. Please use `conda.common.compat`.
"""
from __future__ import absolute_import, division, print_function

from .common.utils import deprecated_import

deprecated_import('conda.common.compat')

import conda.common.compat
from conda.common.compat import *

import sys, warnings

def WrapMod(mod, deprecated):
    """Return a wrapped object that warns about deprecated accesses"""
    deprecated = set(deprecated)

    class Wrapper(object):
        def __getattr__(self, attr):
            if attr in deprecated:
                warnings.warn("Property %s is deprecated" % attr)

            return getattr(mod, attr)

        def __setattr__(self, attr, value):
            if attr in deprecated:
                warnings.warn("Property %s is deprecated" % attr)
            return setattr(mod, attr, value)
    return Wrapper()


sys.modules[__name__] = WrapMod(sys.modules[__name__], deprecated=conda.common.compat.__all__)
