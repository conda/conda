import os
from os.path import isdir, join, abspath
import sys

from conda.cli.common import find_prefix_name


NO_SUCH_DIRECTORY = 70
NO_SUCH_ENVIRONMENT = 75


def prefix_from_arg(arg):
    if os.sep in arg:
        return abspath(arg)
    prefix = find_prefix_name(arg)
    if prefix is None:
        sys.exit(NO_SUCH_ENVIRONMENT)
    return prefix


def binpath_from_arg(arg):
    path = join(prefix_from_arg(arg), 'bin')
    if not isdir(path):
        sys.exit(NO_SUCH_DIRECTORY)
    return path


def prepend_env_path(env_path=None, excluded=None):
    paths = []
    if env_path:
        paths.append(env_path)
    if not excluded:
        excluded = [env_path, ]
    for path in os.getenv('PATH').split(os.pathsep):
        if not path in excluded:
            paths.append(path)
    return paths


def path_string(env_path=None, excluded=None):
    return os.pathsep.join(prepend_env_path(env_path=env_path,
                                            excluded=excluded))
