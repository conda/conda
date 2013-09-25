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
    common.add_parser_json(p)
    p.set_defaults(func=execute)


def execute(args, parser):
    import sys
    import json

    from conda.bundle import create_bundle


    prefix = common.get_prefix(args)
    out_path, warnings = create_bundle(prefix, args.path)

    if args.json:
        d = dict(path=out_path, warnings=warnings)
        json.dump(d, sys.stdout, indent=2, sort_keys=True)
    else:
        for w in warnings:
            print("Warning:", w)
        print(out_path)
