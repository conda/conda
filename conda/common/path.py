# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
import re
import subprocess
from functools import lru_cache, reduce
from itertools import accumulate, chain
from logging import getLogger
from os.path import (
    abspath,
    basename,
    expanduser,
    expandvars,
    join,
    normcase,
    split,
    splitext,
)
from typing import Iterable, Sequence
from urllib.parse import urlsplit

from .. import CondaError
from ..deprecations import deprecated
from .compat import on_win

log = getLogger(__name__)

PATH_MATCH_REGEX = (
    r"\./"  # ./
    r"|\.\."  # ..
    r"|~"  # ~
    r"|/"  # /
    r"|[a-zA-Z]:[/\\]"  # drive letter, colon, forward or backslash
    r"|\\\\"  # windows UNC path
    r"|//"  # windows UNC path
)

# any other extension will be mangled by CondaSession.get() as it tries to find
# channel names from URLs, through strip_pkg_extension()
KNOWN_EXTENSIONS = (".conda", ".tar.bz2", ".json", ".jlap", ".json.zst")


def is_path(value):
    if "://" in value:
        return False
    return re.match(PATH_MATCH_REGEX, value)


def expand(path):
    return abspath(expanduser(expandvars(path)))


def paths_equal(path1, path2):
    """
    Examples:
        >>> paths_equal('/a/b/c', '/a/b/c/d/..')
        True

    """
    if on_win:
        return normcase(abspath(path1)) == normcase(abspath(path2))
    else:
        return abspath(path1) == abspath(path2)


@lru_cache(maxsize=None)
def url_to_path(url):
    """Convert a file:// URL to a path.

    Relative file URLs (i.e. `file:relative/path`) are not supported.
    """
    if is_path(url):
        return url
    if not url.startswith("file://"):  # pragma: no cover
        raise CondaError(
            "You can only turn absolute file: urls into paths (not %s)" % url
        )
    _, netloc, path, _, _ = urlsplit(url)
    from .url import percent_decode

    path = percent_decode(path)
    if netloc not in ("", "localhost", "127.0.0.1", "::1"):
        if not netloc.startswith("\\\\"):
            # The only net location potentially accessible is a Windows UNC path
            netloc = "//" + netloc
    else:
        netloc = ""
        # Handle Windows drive letters if present
        if re.match("^/([a-z])[:|]", path, re.I):
            path = path[1] + ":" + path[3:]
    return netloc + path


def tokenized_startswith(test_iterable, startswith_iterable):
    return all(t == sw for t, sw in zip(test_iterable, startswith_iterable))


def get_all_directories(files: Iterable[str]) -> list[tuple[str]]:
    return sorted({tuple(f.split("/")[:-1]) for f in files} - {()})


def get_leaf_directories(files: Iterable[str]) -> Sequence[str]:
    # give this function a list of files, and it will hand back a list of leaf
    # directories to pass to os.makedirs()
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

    return tuple("/".join(leaf) for leaf in leaves)


@deprecated.argument("23.3", "23.9", "already_split")
def explode_directories(child_directories: Iterable[tuple[str, ...]]) -> set[str]:
    # get all directories including parents
    # child_directories must already be split with os.path.split
    return set(
        chain.from_iterable(
            accumulate(directory, join) for directory in child_directories if directory
        )
    )


def pyc_path(py_path, python_major_minor_version):
    """
    This must not return backslashes on Windows as that will break
    tests and leads to an eventual need to make url_to_path return
    backslashes too and that may end up changing files on disc or
    to the result of comparisons with the contents of them.
    """
    pyver_string = python_major_minor_version.replace(".", "")
    if pyver_string.startswith("2"):
        return py_path + "c"
    else:
        directory, py_file = split(py_path)
        basename_root, extension = splitext(py_file)
        pyc_file = (
            "__pycache__" + "/" + f"{basename_root}.cpython-{pyver_string}{extension}c"
        )
        return "{}{}{}".format(directory, "/", pyc_file) if directory else pyc_file


def missing_pyc_files(python_major_minor_version, files):
    # returns a tuple of tuples, with the inner tuple being the .py file and the missing .pyc file
    py_files = (f for f in files if f.endswith(".py"))
    pyc_matches = (
        (py_file, pyc_path(py_file, python_major_minor_version)) for py_file in py_files
    )
    result = tuple(match for match in pyc_matches if match[1] not in files)
    return result


def parse_entry_point_def(ep_definition):
    cmd_mod, func = ep_definition.rsplit(":", 1)
    command, module = cmd_mod.rsplit("=", 1)
    command, module, func = command.strip(), module.strip(), func.strip()
    return command, module, func


def get_python_short_path(python_version=None):
    if on_win:
        return "python.exe"
    if python_version and "." not in python_version:
        python_version = ".".join(python_version)
    return join("bin", "python%s" % (python_version or ""))


def get_python_site_packages_short_path(python_version):
    if python_version is None:
        return None
    elif on_win:
        return "Lib/site-packages"
    else:
        py_ver = get_major_minor_version(python_version)
        return "lib/python%s/site-packages" % py_ver


_VERSION_REGEX = re.compile(r"[0-9]+\.[0-9]+")


def get_major_minor_version(string, with_dot=True):
    # returns None if not found, otherwise two digits as a string
    # should work for
    #   - 3.5.2
    #   - 27
    #   - bin/python2.7
    #   - lib/python34/site-packages/
    # the last two are dangers because windows doesn't have version information there
    assert isinstance(string, str)
    if string.startswith("lib/python"):
        pythonstr = string.split("/")[1]
        start = len("python")
        if len(pythonstr) < start + 2:
            return None
        maj_min = pythonstr[start], pythonstr[start + 1 :]
    elif string.startswith("bin/python"):
        pythonstr = string.split("/")[1]
        start = len("python")
        if len(pythonstr) < start + 3:
            return None
        assert pythonstr[start + 1] == "."
        maj_min = pythonstr[start], pythonstr[start + 2 :]
    else:
        match = _VERSION_REGEX.match(string)
        if match:
            version = match.group(0).split(".")
            maj_min = version[0], version[1]
        else:
            digits = "".join([c for c in string if c.isdigit()])
            if len(digits) < 2:
                return None
            maj_min = digits[0], digits[1:]

    return ".".join(maj_min) if with_dot else "".join(maj_min)


def get_bin_directory_short_path():
    return "Scripts" if on_win else "bin"


def win_path_ok(path):
    return path.replace("/", "\\") if on_win else path


def win_path_double_escape(path):
    return path.replace("\\", "\\\\") if on_win else path


def win_path_backout(path):
    # replace all backslashes except those escaping spaces
    # if we pass a file url, something like file://\\unc\path\on\win, make sure
    #   we clean that up too
    return re.sub(r"(\\(?! ))", r"/", path).replace(":////", "://")


def ensure_pad(name, pad="_"):
    """

    Examples:
        >>> ensure_pad('conda')
        '_conda_'
        >>> ensure_pad('_conda')
        '__conda_'
        >>> ensure_pad('')
        ''

    """
    if not name or name[0] == name[-1] == pad:
        return name
    else:
        return f"{pad}{name}{pad}"


def is_private_env_name(env_name):
    """

    Examples:
        >>> is_private_env_name("_conda")
        False
        >>> is_private_env_name("_conda_")
        True

    """
    return env_name and env_name[0] == env_name[-1] == "_"


def is_private_env_path(env_path):
    """

    Examples:
        >>> is_private_env_path('/some/path/to/envs/_conda_')
        True
        >>> is_private_env_path('/not/an/envs_dir/_conda_')
        False

    """
    if env_path is not None:
        envs_directory, env_name = split(env_path)
        if basename(envs_directory) != "envs":
            return False
        return is_private_env_name(env_name)
    return False


def right_pad_os_sep(path):
    return path if path.endswith(os.sep) else path + os.sep


def split_filename(path_or_url):
    dn, fn = split(path_or_url)
    return (dn or None, fn) if "." in fn else (path_or_url, None)


def get_python_noarch_target_path(source_short_path, target_site_packages_short_path):
    if source_short_path.startswith("site-packages/"):
        sp_dir = target_site_packages_short_path
        return source_short_path.replace("site-packages", sp_dir, 1)
    elif source_short_path.startswith("python-scripts/"):
        bin_dir = get_bin_directory_short_path()
        return source_short_path.replace("python-scripts", bin_dir, 1)
    else:
        return source_short_path


def win_path_to_unix(path, root_prefix=""):
    # If the user wishes to drive conda from MSYS2 itself while also having
    # msys2 packages in their environment this allows the path conversion to
    # happen relative to the actual shell. The onus is on the user to set
    # CYGPATH to e.g. /usr/bin/cygpath.exe (this will be translated to e.g.
    # (C:\msys32\usr\bin\cygpath.exe by MSYS2) to ensure this one is used.
    if not path:
        return ""

    # rebind to shutil to avoid triggering the deprecation warning
    from shutil import which

    bash = which("bash")
    if bash:
        cygpath = os.environ.get(
            "CYGPATH", os.path.join(os.path.dirname(bash), "cygpath.exe")
        )
    else:
        cygpath = os.environ.get("CYGPATH", "cygpath.exe")
    try:
        path = (
            subprocess.check_output([cygpath, "-up", path])
            .decode("ascii")
            .split("\n")[0]
        )
    except Exception as e:
        log.debug("%r" % e, exc_info=True)

        # Convert a path or ;-separated string of paths into a unix representation
        # Does not add cygdrive.  If you need that, set root_prefix to "/cygdrive"
        def _translation(found_path):  # NOQA
            found = (
                found_path.group(1)
                .replace("\\", "/")
                .replace(":", "")
                .replace("//", "/")
            )
            return root_prefix + "/" + found

        path_re = '(?<![:/^a-zA-Z])([a-zA-Z]:[/\\\\]+(?:[^:*?"<>|]+[/\\\\]+)*[^:*?"<>|;/\\\\]+?(?![a-zA-Z]:))'  # noqa
        path = re.sub(path_re, _translation, path).replace(";/", ":/")
    return path


def which(executable):
    """Backwards-compatibility wrapper. Use `shutil.which` directly if possible."""
    from shutil import which

    return which(executable)


def strip_pkg_extension(path: str):
    """
    Examples:
        >>> strip_pkg_extension("/path/_license-1.1-py27_1.tar.bz2")
        ('/path/_license-1.1-py27_1', '.tar.bz2')
        >>> strip_pkg_extension("/path/_license-1.1-py27_1.conda")
        ('/path/_license-1.1-py27_1', '.conda')
        >>> strip_pkg_extension("/path/_license-1.1-py27_1")
        ('/path/_license-1.1-py27_1', None)
    """
    # NOTE: not using CONDA_TARBALL_EXTENSION_V1 or CONDA_TARBALL_EXTENSION_V2 to comply with
    #       import rules and to avoid a global lookup.
    for extension in KNOWN_EXTENSIONS:
        if path.endswith(extension):
            return path[: -len(extension)], extension
    return path, None


def is_package_file(path):
    """
    Examples:
        >>> is_package_file("/path/_license-1.1-py27_1.tar.bz2")
        True
        >>> is_package_file("/path/_license-1.1-py27_1.conda")
        True
        >>> is_package_file("/path/_license-1.1-py27_1")
        False
    """
    # NOTE: not using CONDA_TARBALL_EXTENSION_V1 or CONDA_TARBALL_EXTENSION_V2 to comply with
    #       import rules and to avoid a global lookup.
    return path[-6:] == ".conda" or path[-8:] == ".tar.bz2"
