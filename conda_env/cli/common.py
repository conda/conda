import os
from os.path import isdir, join
import sys

from conda._vendor.auxlib.entity import EntityEncoder
from conda.base.context import context

base_env_name = 'base'


def stdout_json(d):
    import json

    json.dump(d, sys.stdout, indent=2, sort_keys=True, cls=EntityEncoder)
    sys.stdout.write('\n')


def get_prefix(args, search=True):
    from conda.base.context import determine_target_prefix
    return determine_target_prefix(context, args)


def find_prefix_name(name):
    if name == base_env_name:
        return context.root_prefix
    # always search cwd in addition to envs dirs (for relative path access)
    for envs_dir in list(context.envs_dirs) + [os.getcwd(), ]:
        prefix = join(envs_dir, name)
        if isdir(prefix):
            return prefix
    return None
