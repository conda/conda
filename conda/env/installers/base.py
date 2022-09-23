# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from importlib import import_module


class InvalidInstaller(Exception):
    def __init__(self, name):
        super().__init__(f"Unable to load installer for {name}")


def get_installer(name):
    try:
        return import_module(f"{__name__.rsplit('.', 1)[0]}.{name}")
    except ImportError:
        raise InvalidInstaller(name)
