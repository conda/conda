from __future__ import absolute_import, print_function

from argparse import RawDescriptionHelpFormatter
import os
import textwrap

from conda.cli.conda_argparse import add_parser_json, add_parser_prefix

# conda env import
from .common import get_prefix
from ..env import from_environment
from ..exceptions import CondaEnvException

description = """
Export a given environment
"""

example = """
examples:
    conda env export
    conda env export --file SOME_FILE
"""


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'export',
        formatter_class=RawDescriptionHelpFormatter,
        description=description,
        help=description,
        epilog=example,
    )

    p.add_argument(
        '-c', '--channel',
        action='append',
        help='Additional channel to include in the export'
    )

    p.add_argument(
        "--override-channels",
        action="store_true",
        help="Do not include .condarc channels",
    )
    add_parser_prefix(p)

    p.add_argument(
        '-f', '--file',
        default=None,
        required=False
    )

    p.add_argument(
        '--no-builds',
        default=False,
        action='store_true',
        required=False,
        help='Remove build specification from dependencies'
    )

    p.add_argument(
        '--ignore-channels',
        default=False,
        action='store_true',
        required=False,
        help='Do not include channel names with package names.')
    add_parser_json(p)
    p.set_defaults(func='.main_export.execute')


# TODO Make this aware of channels that were used to install packages
def execute(args, parser):
    if not (args.name or args.prefix):
        # Note, this is a hack fofr get_prefix that assumes argparse results
        # TODO Refactor common.get_prefix
        name = os.environ.get('CONDA_DEFAULT_ENV', False)
        if not name:
            msg = "Unable to determine environment\n\n"
            msg += textwrap.dedent("""
                Please re-run this command with one of the following options:

                * Provide an environment name via --name or -n
                * Re-run this command inside an activated conda environment.""").lstrip()
            # TODO Add json support
            raise CondaEnvException(msg)
        args.name = name
    else:
        name = args.name
    prefix = get_prefix(args)
    env = from_environment(name, prefix, no_builds=args.no_builds,
                           ignore_channels=args.ignore_channels)

    if args.override_channels:
        env.remove_channels()

    if args.channel is not None:
        env.add_channels(args.channel)

    if args.file is None:
        print(env.to_yaml())
    else:
        fp = open(args.file, 'wb')
        env.to_yaml(stream=fp)
