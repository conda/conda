# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from . import ftp, http, localfs, s3

#: The list of transport adapter plugins for easier registration with pluggy
plugins = [ftp, http, localfs, s3]
