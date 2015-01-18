from __future__ import absolute_import, print_function
import sys

from conda.envs import utils


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser('..activate')
    p.add_argument(
        'environment'
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    binpath = utils.binpath_from_arg(args.environment)
    sys.stderr.write("prepending %s to PATH\n" % binpath)
    print(utils.path_string(binpath))
