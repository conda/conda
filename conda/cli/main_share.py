import sys
import json
from argparse import RawDescriptionHelpFormatter

from utils import add_parser_prefix, add_parser_output_json, get_prefix

from conda.builder.share import create_bundle


descr = 'Create a "share package" which may be cloned'


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'share',
        formatter_class = RawDescriptionHelpFormatter,
        description = descr,
        help        = descr,
    )
    add_parser_prefix(p)
    add_parser_output_json(p)
    p.set_defaults(func=execute)


def execute(args, parser):
    prefix = get_prefix(args)
    path, warnings = create_bundle(prefix)

    if args.output_json:
        d = dict(path=path, warnings=warnings)
        json.dump(d, sys.stdout, indent=2, sort_keys=True)
    else:
        for w in warnings:
            print "Warning:", w
        print path
