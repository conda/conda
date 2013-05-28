import common
from argparse import RawDescriptionHelpFormatter


descr = 'Launch an application (EXPERIMENTAL)'


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'launch',
        formatter_class = RawDescriptionHelpFormatter,
        description = descr,
        help        = descr,
    )
    common.add_parser_prefix(p)
    common.add_parser_json(p)
    p.add_argument(
        'package_specs',
        metavar = 'package_spec',
        action  = "store",
        nargs   = 1,
        help    = "application package specification",
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    from os.path import join

    from conda.builder.commands import launch


    prefix = common.get_prefix(args)

    package_spec = args.package_specs[0]
    # TODO
    launch(join(prefix, 'App', package_spec))
