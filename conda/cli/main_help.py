# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

import sys


def execute(args, parser):
    if not args.command:
        parser.print_help()
        return
    print("ERROR: The 'conda help' command is deprecated.\n"
          "Instead use 'conda %s --help'." % args.command,
          file=sys.stderr)
    return 1
