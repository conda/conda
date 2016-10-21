# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import, unicode_literals

descr = "Displays a list of available conda commands and their help strings."

example = """
Examples:

    conda help install
"""
def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'help',
        description=descr,
        help=descr,
        epilog=example,
    )
    p.add_argument(
        'command',
        metavar='COMMAND',
        action="store",
        nargs='?',
        help="""Print help information for COMMAND (same as: conda COMMAND
        --help).""",
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    if not args.command:
        parser.print_help()
        return

    import sys
    import subprocess

    subprocess.call([sys.executable, sys.argv[0], args.command, '-h'])
