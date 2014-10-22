from __future__ import print_function, division, absolute_import
import argparse
import sys

from conda.cli.main import args_func

from . import main_list


def create_parser():
    p = argparse.ArgumentParser()
    sub_parsers = p.add_subparsers()

    main_list.configure_parser(sub_parsers)
    return p


def main():
    parser = create_parser()
    args = parser.parse_args()
    return args_func(args, parser)


if __name__ == '__main__':
    sys.exit(main())
