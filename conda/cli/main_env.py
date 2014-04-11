from __future__ import print_function, division, absolute_import
import sys

from conda.cli import common

invalid_cmd = ("Unable to process command, please use one of "
               "the following: {0}\n")
help = "Interact with conda environments"
help_list = "List all known environments"


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser('env',
                               description=help,
                               help=help)

    p.add_argument('cmd', nargs='?', default='list')
    common.add_parser_json(p)

    p.set_defaults(func=execute)


def execute(args, parser):
    if not args.cmd:
        raise Exception("Unable to parse command?")
    if not args.cmd in COMMANDS:
        sys.stderr.write(invalid_cmd.format(", ".join(COMMANDS.keys())))
        return
    return COMMANDS[args.cmd](args, parser)


def env_list(args, parser):
    info_dict = {'envs': []}
    common.handle_envs_list(args, info_dict['envs'])

    if args.json:
        common.stdout_json(info_dict)

COMMANDS = {
    'list': env_list,
}
