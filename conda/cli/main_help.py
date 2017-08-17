# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
from __future__ import absolute_import, division, print_function, unicode_literals

import subprocess
import sys


def execute(args, parser):
    if not args.command:
        parser.print_help()
        return
    subprocess.call([sys.executable, sys.argv[0], args.command, '-h'])  # pragma: no cover
