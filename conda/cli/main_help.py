# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from utils import add_parser_prefix, get_prefix


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'help',
        description = "Displays a list of available conda commands and their help strings.",
        help        = "Displays a list of available conda commands and their help strings.",
    )
    p.set_defaults(func=execute)

def execute(args, parser):
    parser.print_help()
