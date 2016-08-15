import sys
from os.path import abspath, join, isdir, expanduser
from conda.config import root_dir, default_prefix
import os
from conda.base.context import context
from ..exceptions import CondaEnvException
from conda.exceptions import CondaValueError
import textwrap
root_env_name = 'root'
envs_dirs = context.envs_dirs


def stdout_json(d):
    import json

    json.dump(d, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write('\n')


def get_prefix(args, search=True):
    if args.name:
        if '/' in args.name:
            raise CondaValueError("'/' not allowed in environment name: %s" %
                                  args.name, getattr(args, 'json', False))
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
    for envs_dir in list(envs_dirs) + [os.getcwd(), ]:
        prefix = join(envs_dir, name)
        if isdir(prefix):
            return prefix
    return None


def check_specs(prefix, specs, json=False, create=False):
    if len(specs) == 0:
        msg = ('too few arguments, must supply command line '
               'package specs or --file')
        if create:
            msg += textwrap.dedent("""
                You can specify one or more default packages to install when creating
                an environment.  Doing so allows you to call conda create without
                explicitly providing any package names.
                To set the provided packages, call conda config like this:
                    conda config --add create_default_packages PACKAGE_NAME
            """)
        raise CondaEnvException(msg)
