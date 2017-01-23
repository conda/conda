# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from conda.cli.python_api import run_command, Commands

stdout, stderr, rc = run_command(Commands.CREATE, "-n testme --mkdir python --dry-run")
print(">>>")
print(rc)
print(">>>")
print(stdout)
print(">>>")
print(stderr)
