# -*- coding: utf-8 -*-
"""
This module is DEPRECATED. Please use `conda.common.compat`.
"""
from __future__ import absolute_import, division, print_function

from .common.utils import deprecate_module_with_proxy
from conda.common.compat import *  # NOQA

deprecate_module_with_proxy(__name__, locals())
