from __future__ import absolute_import, print_function
import sys
import os

from conda.envs import utils


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser('..deactivate')
    p.set_defaults(func=execute)


def execute(args, parser):
    binpath = utils.binpath_from_arg(os.getenv('CONDA_DEFAULT_ENV', 'root'))
    sys.stderr.write("discarding %s from PATH\n" % binpath)
    print(utils.path_string(binpath))
