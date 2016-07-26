import sys
from os.path import abspath, join, isdir, expanduser
from conda.config import root_dir, default_prefix
import os
from conda.base.context import context

root_env_name = 'root'
envs_dirs = context.envs_dirs
def stdout_json(d):
    import json

    json.dump(d, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write('\n')


def error_and_exit(message, json=False, newline=False, error_text=True,
                   error_type=None):
    """
        Function used in conda info
    """
    if json:
        stdout_json(dict(error=message, error_type=error_type))
        sys.exit(1)
    else:
        if newline:
            print()

        if error_text:
            sys.exit("Error: " + message)
        else:
            sys.exit(message)


def exception_and_exit(exc, **kwargs):
    if 'error_type' not in kwargs:
        kwargs['error_type'] = exc.__class__.__name__
    error_and_exit('; '.join(map(str, exc.args)), **kwargs)


def get_prefix(args, search=True):
    if args.name:
        if '/' in args.name:
            error_and_exit("'/' not allowed in environment name: %s" %
                           args.name,
                           json=getattr(args, 'json', False),
                           error_type="ValueError")
        if args.name == root_env_name:
            return root_dir
        if search:
            prefix = find_prefix_name(args.name)
            if prefix:
                return prefix
        return join(envs_dirs[0], args.name)

    if args.prefix:
        return abspath(expanduser(args.prefix))

    return default_prefix

def find_prefix_name(name):
    if name == root_env_name:
        return root_dir
    # always search cwd in addition to envs dirs (for relative path access)
    for envs_dir in envs_dirs + [os.getcwd(), ]:
        prefix = join(envs_dir, name)
        if isdir(prefix):
            return prefix
    return None