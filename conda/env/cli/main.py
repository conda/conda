from __future__ import print_function, division, absolute_import
import argparse
import os
import sys

from ...cli.main import args_func

from . import main_create
from . import main_export
from . import main_list
from . import main_remove
from . import main_update


def create_parser():
    p = argparse.ArgumentParser()
    sub_parsers = p.add_subparsers()

    main_create.configure_parser(sub_parsers)
    main_export.configure_parser(sub_parsers)
    main_list.configure_parser(sub_parsers)
    main_remove.configure_parser(sub_parsers)
    main_update.configure_parser(sub_parsers)
    return p


def main():
    parser = create_parser()
    args = parser.parse_args()
    return args_func(args, parser)


if __name__ == '__main__':
    sys.exit(main())
