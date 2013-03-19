import sys
import json
from os.path import isfile
from argparse import RawDescriptionHelpFormatter

from utils import add_parser_prefix, add_parser_output_json, get_prefix

from conda.builder.share import clone_bundle


descr = 'Clone a "share package" (created using the share command)'


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'clone',
        formatter_class = RawDescriptionHelpFormatter,
        description = descr,
        help        = descr,
    )
    p.add_argument(
        'path',
        metavar = 'PATH',
        action  = "store",
        nargs   = 1,
        help    = 'path to "share package"',
    )
    add_parser_prefix(p)
    add_parser_output_json(p)
    p.set_defaults(func=execute)


def execute(args, parser):
    if (not args.name) and (not args.prefix):
        raise RuntimeError('either -n NAME or -p PREFIX option required, '
                           'try "conda create -h" for more details')

    prefix = get_prefix(args)
    path = args.path[0]
    if not isfile(path):
        raise RuntimeError("no such file: %s" % path)

    warnings = []
    for w in clone_bundle(path, prefix):
        if args.output_json:
            warnings.append(w)
        else:
            print "Warning:", w
            
    if args.output_json:
        json.dump(warnings, sys.stdout, indent=2)
