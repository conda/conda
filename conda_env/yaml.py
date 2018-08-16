# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Wrapper around yaml to ensure that everything is ordered correctly.

This is based on the answer at http://stackoverflow.com/a/16782282
"""
from __future__ import absolute_import, print_function

from conda.common.compat import odict
from conda.common.serialize import get_yaml, yaml_dump, yaml_load_safe

yaml = get_yaml()

dump = yaml_dump
load = yaml_load_safe
dict = odict
