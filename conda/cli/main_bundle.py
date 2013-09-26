from __future__ import print_function, division, absolute_import

from conda.cli import common
from argparse import RawDescriptionHelpFormatter


descr = 'Create a "bundle package" (EXPERIMENTAL)'


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'bundle',
        formatter_class = RawDescriptionHelpFormatter,
        description = descr,
        help = descr,
    )
    common.add_parser_prefix(p)
    p.add_argument(
        "--path",
        action = "store",
        help = "path to data to be included in bundle",
    )
    p.add_argument(
        "--bundle-name",
        action = "store",
        help = "name of bundle",
        metavar = 'NAME',
    )
    common.add_parser_json(p)
    p.set_defaults(func=execute)


def execute(args, parser):
    import sys
    import json

    from conda.bundle import create_bundle


    prefix = common.get_prefix(args)
    out_path = create_bundle(prefix, args.path, args.bundle_name)

    if args.json:
        d = dict(path=out_path)
        json.dump(d, sys.stdout, indent=2, sort_keys=True)
    else:
        print(out_path)
