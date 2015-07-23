# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

from conda.cli import common, install


help = "Create a new conda environment from a list of specified packages. "
descr = (help +
         "To use the created environment, use 'source activate "
         "envname' look in that directory first.  This command requires either "
         "the -n NAME or -p PREFIX option.")

example = """
Examples:

    conda create -n myenv sqlite

"""

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'create',
        description=descr,
        help=help,
        epilog=example,
    )
    common.add_parser_install(p)
    common.add_parser_json(p)
    p.add_argument(
        "--clone",
        action="store",
        help='Path to (or name of) existing local environment.',
        metavar='ENV',
    )
    p.add_argument(
        "--no-default-packages",
        action="store_true",
        help='Ignore create_default_packages in the .condarc file.',
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    install.install(args, parser, 'create')
