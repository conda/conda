# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from ..._preview.env_setup.cli import main_create, main_install
from . import doctor

plugins = [doctor, main_create, main_install]
