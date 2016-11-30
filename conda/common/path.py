# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from functools import reduce
from logging import getLogger
from os.path import basename, dirname, join

from ..utils import on_win

try:
    from cytoolz.itertoolz import accumulate, concat
except ImportError:
    from .._vendor.toolz.itertoolz import accumulate, concat


log = getLogger(__name__)


def tokenized_startswith(test_iterable, startswith_iterable):
    return all(t == sw for t, sw in zip(test_iterable, startswith_iterable))


def get_leaf_directories(files):
    # type: (List[str]) -> List[str]
    # give this function a list of files, and it will hand back a list of leaf directories to
    # pass to os.makedirs()
    directories = sorted(set(tuple(f.split('/')[:-1]) for f in files))
    if not directories:
        return ()

    leaves = []

    def _process(x, y):
        if not tokenized_startswith(y, x):
            leaves.append(x)
        return y
    last = reduce(_process, directories)

    if not leaves:
        leaves.append(directories[-1])
    elif not tokenized_startswith(last, leaves[-1]):
        leaves.append(last)

    return tuple('/'.join(leaf) for leaf in leaves)


def explode_directories(child_directories):
    # get all directories including parents
    return set(concat(accumulate(join, directory.split('/')) for directory in child_directories))


def missing_pyc_files(python_major_minor_version, files):
    # returns a tuple of tuples, with the inner tuple being the .py file and the missing .pyc file
    pyver_string = python_major_minor_version.replace('.', '')

    def pyc_path(file):
        if python_major_minor_version.startswith('2'):
            return file + "c"
        else:
            base_fn, base_extention = basename(file).rsplit('.', 1)
            return "%s/__pycache__/%s.cpython-%s.%sc" % (dirname(file), base_fn, pyver_string,
                                                         base_extention)

    py_files = (f for f in files if f.endswith('.py'))
    pyc_matches = ((py_file, pyc_path(py_file)) for py_file in py_files)
    result = tuple(match for match in pyc_matches if match[1] not in files)
    return result


def parse_entry_point_def(ep_definition):
    cmd_mod, func = ep_definition.rsplit(':', 1)
    command, module = cmd_mod.rsplit("=", 1)
    command, module, func = command.strip(), module.strip(), func.strip()
    return command, module, func


def get_python_path():
    return "python.exe" if on_win else join("bin", "python")


def get_bin_directory_short_path():
    return 'Scripts' if on_win else 'bin'


def win_path_ok(path):
    return path.replace('/', '\\') if on_win else path


def win_path_double_escape(path):
    return path.replace('\\', '\\\\') if on_win else path


def maybe_pad(name, pad="_"):
    new_name = name if name.startswith(pad) else "%s%s" % (pad, name)
    new_name = new_name if name.endswith(pad) else "%s%s" % (new_name, pad)
    return new_name


def preferred_env_to_prefix(preferred_env, root_dir, envs_dirs):
    if preferred_env is None:
        return root_dir
    else:
        return join(envs_dirs[0], maybe_pad(preferred_env, '_'))


def prefix_to_env_name(prefix):
    split_env = prefix.split("/envs/")
    if len(split_env) == 1:
        return None
    return split_env[-1]


def preferred_env_matches_prefix(preferred_env, prefix, root_dir):
    # type (str, str) -> bool
    if preferred_env is None:
        return True
    prefix_dir = dirname(prefix)
    if prefix_dir != join(root_dir, 'envs'):
        return False
    prefix_name = basename(prefix)
    padded_preferred_env = maybe_pad(preferred_env)
    return prefix_name == padded_preferred_env


def is_private_env(env):
    if env is not None and env.startswith("_") and env.endswith("_"):
        return True
    return False
