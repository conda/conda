import os
from os.path import abspath, expanduser, join

from conda.config import ROOT_DIR



def get_default_prefix():
    name = os.getenv('CONDA_DEFAULT_ENV')
    if name:
        return join(ROOT_DIR, 'envs', name)
    else:
        return ROOT_DIR


def get_prefix(args):
    if args.name:
        return join(ROOT_DIR, 'envs', args.name)

    if args.prefix:
        return abspath(expanduser(args.prefix))

    return get_default_prefix()
