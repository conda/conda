# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import os
from functools import reduce
from logging import getLogger
from os.path import basename, join, splitext, split

from .compat import string_types
from ..utils import on_win

try:
    from cytoolz.itertoolz import accumulate, concat, take
except ImportError:
    from .._vendor.toolz.itertoolz import accumulate, concat, take


log = getLogger(__name__)


def tokenized_startswith(test_iterable, startswith_iterable):
    return all(t == sw for t, sw in zip(test_iterable, startswith_iterable))


def get_all_directories(files):
    directories = sorted(set(tuple(f.split('/')[:-1]) for f in files))
    return directories or ()


def get_leaf_directories(files):
    # type: (List[str]) -> List[str]
    # give this function a list of files, and it will hand back a list of leaf directories to
    #   pass to os.makedirs()
    directories = get_all_directories(files)
    if not directories:
        return ()

    leaves = []
    def _process(x, y):  # NOQA
        if not tokenized_startswith(y, x):
            leaves.append(x)
        return y
    last = reduce(_process, directories)

    if not leaves:
        leaves.append(directories[-1])
    elif not tokenized_startswith(last, leaves[-1]):
        leaves.append(last)

    return tuple('/'.join(leaf) for leaf in leaves)


def explode_directories(child_directories, already_split=False):
    # get all directories including parents
    # use already_split=True for the result of get_all_directories()
    maybe_split = lambda x: x if already_split else x.split('/')
    return set(concat(accumulate(join, maybe_split(directory)) for directory in child_directories))


def pyc_path(py_path, python_major_minor_version):
    pyver_string = python_major_minor_version.replace('.', '')
    if pyver_string.startswith('2'):
        return py_path + 'c'
    else:
        directory, py_file = split(py_path)
        basename_root, extension = splitext(py_file)
        pyc_file = "__pycache__/%s.cpython-%s%sc" % (basename_root, pyver_string, extension)
        return "%s/%s" % (directory, pyc_file) if directory else pyc_file


def missing_pyc_files(python_major_minor_version, files):
    # returns a tuple of tuples, with the inner tuple being the .py file and the missing .pyc file
    py_files = (f for f in files if f.endswith('.py'))
    pyc_matches = ((py_file, pyc_path(py_file, python_major_minor_version))
                   for py_file in py_files)
    result = tuple(match for match in pyc_matches if match[1] not in files)
    return result


def parse_entry_point_def(ep_definition):
    cmd_mod, func = ep_definition.rsplit(':', 1)
    command, module = cmd_mod.rsplit("=", 1)
    command, module, func = command.strip(), module.strip(), func.strip()
    return command, module, func


def get_python_path(version=None):
    if on_win:
        return "python.exe"
    if version and '.' not in version:
        version = '.'.join(version)
    return join("bin", "python%s" % version or '')


def get_python_site_packages_short_path(python_version):
    if python_version is None:
        return None
    elif on_win:
        return 'Lib/site-packages'
    else:
        py_ver = get_major_minor_version(python_version)
        return 'lib/python%s/site-packages' % py_ver


def get_major_minor_version(string, with_dot=True):
    # returns None if not found, otherwise two digits as a string
    # should work for
    #   - 3.5.2
    #   - 27
    #   - bin/python2.7
    #   - lib/python34/site-packages/
    # the last two are dangers because windows doesn't have version information there
    assert isinstance(string, string_types)
    digits = tuple(take(2, (c for c in string if c.isdigit())))
    if len(digits) == 2:
        return '.'.join(digits) if with_dot else ''.join(digits)
    return None


def get_bin_directory_short_path():
    return 'Scripts' if on_win else 'bin'


def win_path_ok(path):
    return path.replace('/', '\\') if on_win else path


def win_path_double_escape(path):
    return path.replace('\\', '\\\\') if on_win else path


def win_path_backout(path):
    return path.replace('\\', '/') if on_win else path


def right_pad_os_sep(path):
    return path if path.endswith(os.sep) else path + os.sep
