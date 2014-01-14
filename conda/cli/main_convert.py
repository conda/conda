# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import os
from argparse import RawDescriptionHelpFormatter

from conda.cli import common
from conda.convert import show_cext

import tarfile

help = "Various tools to convert conda packages."
example = ''

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'convert',
        formatter_class = RawDescriptionHelpFormatter,
        description = help,
        help = help,
        epilog = example,
    )

    p.add_argument(
        'package-file',
        metavar = 'package_file',
        action = "store",
        nargs = '*',
        help = "package versions to install into conda environment",
    )
    p.set_defaults(func=execute)



def execute(args, parser):
    file = parser.package_file
    print(file)
