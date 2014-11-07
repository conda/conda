from __future__ import print_function, division, absolute_import
import argparse
import os
import sys

from . import main_create
from . import main_export
from . import main_list
from . import main_remove
from . import main_update

import sys

CMDS = {
    'create': main_create,
    'export': main_export,
    'list': main_list,
    'remove': main_remove,
    'update': main_update,
}


# TODO: This should be somewhere in conda.cli
def show_help_on_empty_command(cmd):
    args = sys.argv[1:]
    if cmd not in args:
        return  # Only set default if help
    if len(args) == 1 and args[0] == cmd:
        sys.argv.append('--help')


def configure_parser(main_sub_parsers):
    p = main_sub_parsers.add_parser(
        'env',
        help='Commands for interacting with Conda environments',
    )
    sub_parsers = p.add_subparsers(
        title='conda env',
        description='commands for interacting with conda env',
        dest='env_subcommand',
    )

    for a in CMDS.values():
        a.configure_parser(sub_parsers)

    p.set_defaults(func=execute)
    show_help_on_empty_command('env')
    return p


def execute(args, parser):
    return CMDS[args.env_subcommand].execute(args, parser)
