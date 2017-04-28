import os
from os.path import isdir, join
import sys

from conda._vendor.auxlib.entity import EntityEncoder
from conda.base.context import context, get_prefix as context_get_prefix
from conda.config import root_dir

root_env_name = 'root'


def stdout_json(d):
    import json

    json.dump(d, sys.stdout, indent=2, sort_keys=True, cls=EntityEncoder)
    sys.stdout.write('\n')


def get_prefix(args, search=True):
    return context_get_prefix(context, args, search)


def find_prefix_name(name):
    if name == root_env_name:
        return root_dir
    # always search cwd in addition to envs dirs (for relative path access)
    for envs_dir in list(context.envs_dirs) + [os.getcwd(), ]:
        prefix = join(envs_dir, name)
        if isdir(prefix):
            return prefix
    return None
