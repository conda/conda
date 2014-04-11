from __future__ import print_function, division, absolute_import

from conda.cli import common

help = "List all known environments"


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser('envs',
                               description=help,
                               help=help)
    common.add_parser_json(p)
    p.set_defaults(func=execute)


def execute(args, parser):
    info_dict = {'envs': []}
    common.handle_envs_list(args, info_dict['envs'])

    if args.json:
        common.stdout_json(info_dict)
