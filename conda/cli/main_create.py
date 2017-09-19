# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import absolute_import, division, print_function, unicode_literals

from .install import install
from ..gateways.disk.delete import delete_trash


def execute(args, parser):
    install(args, parser, 'create')
    delete_trash()
