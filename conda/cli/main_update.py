# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

from conda.cli import common, install


descr = "Update conda packages to the current version."
example = """
Examples:

    conda %s -n myenv scipy

"""

alias_help = "Alias for conda update.  See conda update --help."

def configure_parser(sub_parsers, name='update'):
    if name == 'update':
        p = sub_parsers.add_parser(
            'update',
            description=descr,
            help=descr,
            epilog=example % name,
        )
    else:
        p = sub_parsers.add_parser(
            name,
            description=alias_help,
            help=alias_help,
            epilog=example % name,
        )
    common.add_parser_install(p)
    common.add_parser_json(p)
    p.add_argument(
        "--all",
        action="store_true",
        help="Update all installed packages in the environment.",
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    install.install(args, parser, 'update')
