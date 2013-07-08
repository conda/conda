from __future__ import print_function, division, absolute_import

from . import common
from argparse import RawDescriptionHelpFormatter


descr = 'Clone a "share package" (created using the share command)'


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'clone',
        formatter_class = RawDescriptionHelpFormatter,
        description = descr,
        help = descr,
    )
    p.add_argument(
        'path',
        metavar = 'PATH',
        action  = "store",
        nargs   = 1,
        help    = 'path to "share package"',
    )
    common.add_parser_prefix(p)
    common.add_parser_json(p)
    p.set_defaults(func=execute)


def execute(args, parser):
    import sys
    import json
    from os.path import isfile

    from conda.builder.share import clone_bundle


    common.ensure_name_or_prefix(args, 'clone')

    prefix = common.get_prefix(args)

    path = args.path[0]
    if not isfile(path):
        sys.exit("Error: no such file: %s" % path)

    clone_bundle(path, prefix)

    if args.json:
        json.dump(dict(warnings=[]), sys.stdout, indent=2)
