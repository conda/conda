# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import absolute_import, division, print_function, unicode_literals

import sys

from .install import install
from ..base.context import context
from ..gateways.disk.delete import delete_trash


def execute(args, parser):
    if context.force:
        print("\n\n"
              "WARNING: The --force flag will be removed in a future conda release.\n"
              "         See 'conda install --help' for details about the --force-reinstall\n"
              "         and --clobber flags.\n"
              "\n", file=sys.stderr)

    install(args, parser, 'install')
    delete_trash()
