# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from functools import reduce
import os
from os.path import basename, dirname, join, split, splitext
import re

from .compat import on_win, string_types
from .. import CondaError
from .._vendor.auxlib.decorators import memoize

try:
    # Python 3
    from urllib.parse import unquote, urlsplit
    from urllib.request import url2pathname
except ImportError:
    # Python 2
    from urllib import unquote, url2pathname  # NOQA
    from urlparse import urlsplit  # NOQA

try:
    from cytoolz.itertoolz import accumulate, concat, take
except ImportError:
    from .._vendor.toolz.itertoolz import accumulate, concat, take


PATH_MATCH_REGEX = (
    r"\./"              # ./
    r"|\.\."            # ..
    r"|~"               # ~
    r"|/"               # /
    r"|[a-zA-Z]:[/\\]"  # drive letter, colon, forward or backslash
    r"|\\\\"            # windows UNC path
    r"|//"              # windows UNC path
)


def is_path(value):
    if '://' in value:
        return False
    return re.match(PATH_MATCH_REGEX, value)


@memoize
def url_to_path(url):
    """Convert a file:// URL to a path.

    Relative file URLs (i.e. `file:relative/path`) are not supported.
    """
    if is_path(url):
        return url
    if not url.startswith("file://"):
        raise CondaError("You can only turn absolute file: urls into paths (not %s)" % url)
    _, netloc, path, _, _ = urlsplit(url)
    path = unquote(path)
    if netloc not in ('', 'localhost', '127.0.0.1', '::1'):
        if not netloc.startswith('\\\\'):
            # The only net location potentially accessible is a Windows UNC path
            netloc = '//' + netloc
    else:
        netloc = ''
        # Handle Windows drive letters if present
        if re.match('^/([a-z])[:|]', path, re.I):
            path = path[1] + ':' + path[3:]
    return netloc + path


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


def get_python_short_path(python_version=None):
    if on_win:
        return "python.exe"
    if python_version and '.' not in python_version:
        python_version = '.'.join(python_version)
    return join("bin", "python%s" % (python_version or ''))


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
    # replace all backslashes except those escaping spaces
    # if we pass a file url, something like file://\\unc\path\on\win, make sure
    #   we clean that up too
    return re.sub(r"(\\(?! ))", r"/", path).replace(':////', '://')


def ensure_pad(name, pad="_"):
    return "%s%s%s" % (pad, name.strip(pad), pad)


def preferred_env_to_prefix(preferred_env, root_dir, envs_dirs):
    if preferred_env is None:
        return root_dir
    else:
        return '/'.join((envs_dirs[0], ensure_pad(preferred_env, '_')))


def prefix_to_env_name(prefix, root_prefix):
    if prefix == root_prefix:
        return None
    split_env = win_path_backout(prefix).split("/")
    return split_env[-1]


def preferred_env_matches_prefix(preferred_env, prefix, root_dir):
    # type: (str, str, str) -> bool
    if preferred_env is None:
        return True
    prefix_dir = dirname(prefix)
    if prefix_dir != join(root_dir, 'envs'):
        return False
    prefix_name = basename(prefix)
    padded_preferred_env = ensure_pad(preferred_env)
    return prefix_name == padded_preferred_env


def is_private_env(env):
    if env is not None:
        env_name = basename(env)
        if env_name.startswith("_") and env_name.endswith("_"):
            return True
    return False


def right_pad_os_sep(path):
    return path if path.endswith(os.sep) else path + os.sep


def split_filename(path_or_url):
    dn, fn = split(path_or_url)
    return (dn or None, fn) if '.' in fn else (path_or_url, None)


def get_python_noarch_target_path(source_short_path, target_site_packages_short_path):
    if source_short_path.startswith('site-packages/'):
        sp_dir = target_site_packages_short_path
        return source_short_path.replace('site-packages', sp_dir, 1)
    elif source_short_path.startswith('python-scripts/'):
        bin_dir = get_bin_directory_short_path()
        return source_short_path.replace('python-scripts', bin_dir, 1)
    else:
        return source_short_path
