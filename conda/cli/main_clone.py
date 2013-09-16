from __future__ import print_function, division, absolute_import

from conda.cli import common
from argparse import RawDescriptionHelpFormatter


descr = ('Clone an existing environment or a "share package" '
         '(created by conda package --share)')

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
        action = "store",
        nargs = 1,
        help = 'path existing environment or "share package"',
    )
    common.add_parser_prefix(p)
    common.add_parser_json(p)
    p.set_defaults(func=execute)


def execute(args, parser):
    import sys
    import json
    from os.path import exists, isdir, isfile


    common.ensure_name_or_prefix(args, 'clone')

    prefix = common.get_prefix(args, search=False)
    if exists(prefix):
        sys.exit("Error: prefix already exists: %s" % prefix)

    path = args.path[0]
    if isfile(path):
        from conda.builder.share import clone_bundle
        clone_bundle(path, prefix)
        if args.json:
            json.dump(dict(warnings=[]), sys.stdout, indent=2)

    elif isdir(path):
        from conda.misc import clone_env
        clone_env(path, prefix)

    else:
        sys.exit("Error: no such file or directory: %s" % path)
