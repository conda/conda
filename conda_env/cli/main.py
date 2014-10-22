from __future__ import print_function, division, absolute_import
import argparse
from argparse import RawDescriptionHelpFormatter
import sys

from conda.cli import common


description = """
Handles interacting with Conda environments.
"""

example = """
examples:
    conda env list
    conda env list --json
"""


def configure_parser():
    p = argparse.ArgumentParser()
    sub_parsers = p.add_subparsers()

    l = sub_parsers.add_parser(
        'list',
        formatter_class=RawDescriptionHelpFormatter,
        description=description,
        help=description,
        epilog=example,
    )

    common.add_parser_json(l)

    return p


def main():
    args = configure_parser().parse_args()
    info_dict = {'envs': []}
    common.handle_envs_list(info_dict['envs'], not args.json)

    if args.json:
        common.stdout_json(info_dict)


if __name__ == '__main__':
    sys.exit(main())
