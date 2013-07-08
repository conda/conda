from __future__ import print_function, division, absolute_import

import common
from argparse import RawDescriptionHelpFormatter


descr = 'Create a "share package" which may be cloned'


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'share',
        formatter_class = RawDescriptionHelpFormatter,
        description = descr,
        help = descr,
    )
    common.add_parser_prefix(p)
    common.add_parser_json(p)
    p.set_defaults(func=execute)


def execute(args, parser):
    import sys
    import json

    from conda.builder.share import create_bundle


    prefix = common.get_prefix(args)
    path, warnings = create_bundle(prefix)

    if args.json:
        d = dict(path=path, warnings=warnings)
        json.dump(d, sys.stdout, indent=2, sort_keys=True)
    else:
        for w in warnings:
            print "Warning:", w
        print path
