from os.path import join
from argparse import RawDescriptionHelpFormatter

from utils import add_parser_prefix, add_parser_json, get_prefix

from conda.builder.commands import launch


descr = 'Launch an application (EXPERIMENTAL)'


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'launch',
        formatter_class = RawDescriptionHelpFormatter,
        description = descr,
        help        = descr,
    )
    add_parser_prefix(p)
    add_parser_json(p)
    p.add_argument(
        'package_specs',
        metavar = 'package_spec',
        action  = "store",
        nargs   = 1,
        help    = "application package specification",
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    prefix = get_prefix(args)

    package_spec = args.package_specs[0]
    # TODO
    launch(join(prefix, 'App', package_spec))
