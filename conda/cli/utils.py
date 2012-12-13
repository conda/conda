import os
from os.path import abspath, expanduser, join

from conda.config import ROOT_DIR


def get_default_prefix():
    name = os.getenv('CONDA_DEFAULT_ENV')
    if name:
        return join(ROOT_DIR, 'envs', name)
    else:
        return ROOT_DIR


def add_parser_prefix(p):
    npgroup = p.add_mutually_exclusive_group()
    npgroup.add_argument(
        '-n', "--name",
        action  = "store",
        help    = "name of environment (directory in %s/envs)" %
                  ROOT_DIR,
    )
    npgroup.add_argument(
        '-p', "--prefix",
        action  = "store",
        help    = "full path to environment prefix (default: %s)" %
                  get_default_prefix(),
    )


def get_prefix(args):
    if args.name:
        return join(ROOT_DIR, 'envs', args.name)

    if args.prefix:
        return abspath(expanduser(args.prefix))

    return get_default_prefix()
