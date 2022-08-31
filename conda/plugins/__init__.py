# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import pluggy

from . import specs
from .specs import CondaSubcommand  # noqa: F401


register = pluggy.HookimplMarker("conda")

manager = pluggy.PluginManager("conda")
manager.add_hookspecs(specs)
manager.load_setuptools_entrypoints("conda")
