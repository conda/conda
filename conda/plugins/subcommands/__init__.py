# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from importlib import import_module

from . import doctor

plugins = [doctor, import_module(f"{__name__}.plugins")]
