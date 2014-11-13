from __future__ import absolute_import, print_function
import sys
import os

from conda import config
# TODO Move this to its new home once its found
from conda.cli.activate import binpath_from_arg
from conda.envs import utils


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser('..activateroot')
    p.set_defaults(func=execute)


def execute(args, parser):
    if 'CONDA_DEFAULT_ENV' not in os.environ:
        sys.exit("Error: No environment to deactivate")
    try:
        binpath = binpath_from_arg(os.getenv('CONDA_DEFAULT_ENV'))
        rootpath = binpath_from_arg(config.root_env_name)
    except SystemExit:
        # TODO How does it get to this state?
        print(os.environ['PATH'])
        raise

    # deactivate is the same as activate root (except without setting
    # CONDA_DEFAULT_ENV or PS1). XXX: The user might want to put the root
    # env back somewhere in the middle of the PATH, not at the beginning.
    if rootpath in os.getenv('PATH').split(os.pathsep):
        rootpath = ""

    sys.stderr.write("discarding %s from PATH\n" % binpath)
    print(utils.path_string(excluded=[binpath, ]))
