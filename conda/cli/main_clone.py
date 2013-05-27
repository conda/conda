import utils
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
    utils.add_parser_prefix(p)
    utils.add_parser_json(p)
    p.set_defaults(func=execute)


def execute(args, parser):
    import sys
    import json
    from os.path import isfile

    from conda.builder.share import clone_bundle


    utils.ensure_name_or_prefix(args, 'clone')

    prefix = utils.get_prefix(args)

    path = args.path[0]
    if not isfile(path):
        sys.exit("Error: no such file: %s" % path)

    warnings = []
    for w in clone_bundle(path, prefix):
        if args.json:
            warnings.append(w)
        else:
            print "Warning:", w

    if args.json:
        json.dump(dict(warnings=warnings), sys.stdout, indent=2)
