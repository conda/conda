# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Utility functions."""

from __future__ import annotations

import logging
import re
import sys
from functools import cache, wraps
from os import environ
from os.path import abspath, basename, dirname, isfile, join
from pathlib import Path
from shutil import which

from . import CondaError
from .auxlib.compat import Utf8NamedTemporaryFile, shlex_split_unicode
from .common.compat import isiterable, on_win
from .common.url import path_to_url
from .deprecations import deprecated

log = logging.getLogger(__name__)


@deprecated(
    "25.3",
    "26.3",
    addendum="Use `conda.common.path.unix_path_to_win` instead.",
)
def unix_path_to_win(path, root_prefix=""):
    """Convert a path or :-separated string of paths into a Windows representation
    Does not add cygdrive.  If you need that, set root_prefix to "/cygdrive"
    """
    if len(path) > 1 and (";" in path or (path[1] == ":" and path.count(":") == 1)):
        # already a windows path
        return path.replace("/", "\\")
    path_re = root_prefix + r'(/[a-zA-Z]/(?:(?![:\s]/)[^:*?"<>])*)'

    def _translation(found_path):
        group = found_path.group(0)
        return "{}:{}".format(
            group[len(root_prefix) + 1],
            group[len(root_prefix) + 2 :].replace("/", "\\"),
        )

    translation = re.sub(path_re, _translation, path)
    translation = re.sub(
        ":([a-zA-Z]):\\\\", lambda match: ";" + match.group(0)[1] + ":\\", translation
    )
    return translation


deprecated.constant("25.3", "26.3", "unix_path_to_win", unix_path_to_win)
del unix_path_to_win


def human_bytes(n):
    """
    Return the number of bytes n in more human readable form.

    Examples:
        >>> human_bytes(42)
        '42 B'
        >>> human_bytes(1042)
        '1 KB'
        >>> human_bytes(10004242)
        '9.5 MB'
        >>> human_bytes(100000004242)
        '93.13 GB'
    """
    if n < 1024:
        return "%d B" % n
    k = n / 1024
    if k < 1024:
        return "%d KB" % round(k)
    m = k / 1024
    if m < 1024:
        return f"{m:.1f} MB"
    g = m / 1024
    return f"{g:.2f} GB"


# ##########################################
# put back because of conda build
# ##########################################

urlpath = url_path = path_to_url


@cache
def sys_prefix_unfollowed():
    """Since conda is installed into non-root environments as a symlink only
    and because sys.prefix follows symlinks, this function can be used to
    get the 'unfollowed' sys.prefix.

    This value is usually the same as the prefix of the environment into
    which conda has been symlinked. An example of when this is necessary
    is when conda looks for external sub-commands in find_commands.py
    """
    try:
        frame = next(iter(sys._current_frames().values()))
        while frame.f_back:
            frame = frame.f_back
        code = frame.f_code
        filename = code.co_filename
        unfollowed = dirname(dirname(filename))
    except Exception:
        return sys.prefix
    return unfollowed


def quote_for_shell(*arguments):
    """Properly quote arguments for command line passing.

    For POSIX uses `shlex.join`, for Windows uses a custom implementation to properly escape
    metacharacters.

    :param arguments: Arguments to quote.
    :type arguments: list of str
    :return: Quoted arguments.
    :rtype: str
    """
    # [backport] Support passing in a list of strings or args of string.
    if len(arguments) == 1 and isiterable(arguments[0]):
        arguments = arguments[0]

    return _args_join(arguments)


if on_win:
    # https://ss64.com/nt/syntax-esc.html
    # https://docs.microsoft.com/en-us/archive/blogs/twistylittlepassagesallalike/everyone-quotes-command-line-arguments-the-wrong-way

    _RE_UNSAFE = re.compile(r'["%\s^<>&|]')
    _RE_DBL = re.compile(r'(["%])')

    def _args_join(args):
        """Return a shell-escaped string from *args*."""

        def quote(s):
            # derived from shlex.quote
            if not s:
                return '""'
            # if any unsafe chars are present we must quote
            if not _RE_UNSAFE.search(s):
                return s
            # double escape (" -> "")
            s = _RE_DBL.sub(r"\1\1", s)
            # quote entire string
            return f'"{s}"'

        return " ".join(quote(arg) for arg in args)

else:
    from shlex import join as _args_join


# Ensures arguments are a tuple or a list. Strings are converted
# by shlex_split_unicode() which is bad; we warn about it or else
# we assert (and fix the code).
def massage_arguments(arguments, errors="assert"):
    # For reference and in-case anything breaks ..
    # .. one of the places (run_command in conda_env/utils.py) this
    # gets called from used to do this too:
    #
    #    def escape_for_winpath(p):
    #        return p.replace('\\', '\\\\')
    #
    #    if not isinstance(arguments, list):
    #        arguments = list(map(escape_for_winpath, arguments))

    if isinstance(arguments, str):
        if errors == "assert":
            # This should be something like 'conda programming bug', it is an assert
            assert False, "Please ensure arguments are not strings"
        else:
            arguments = shlex_split_unicode(arguments)
            log.warning(
                "Please ensure arguments is not a string; "
                "used `shlex_split_unicode()` on it"
            )

    if not isiterable(arguments):
        arguments = (arguments,)

    assert not any([isiterable(arg) for arg in arguments]), (
        "Individual arguments must not be iterable"
    )
    arguments = list(arguments)

    return arguments


def wrap_subprocess_call(
    root_prefix,
    prefix,
    dev_mode,
    debug_wrapper_scripts,
    arguments,
    use_system_tmp_path=False,
):
    arguments = massage_arguments(arguments)
    if not use_system_tmp_path:
        tmp_prefix = abspath(join(prefix, ".tmp"))
    else:
        tmp_prefix = None
    script_caller = None
    multiline = False
    if len(arguments) == 1 and "\n" in arguments[0]:
        multiline = True
    if on_win:
        comspec = get_comspec()  # fail early with KeyError if undefined
        if dev_mode:
            from . import CONDA_PACKAGE_ROOT

            conda_bat = join(CONDA_PACKAGE_ROOT, "shell", "condabin", "conda.bat")
        else:
            conda_bat = environ.get(
                "CONDA_BAT", abspath(join(root_prefix, "condabin", "conda.bat"))
            )
        with Utf8NamedTemporaryFile(
            mode="w", prefix=tmp_prefix, suffix=".bat", delete=False
        ) as fh:
            silencer = "" if debug_wrapper_scripts else "@"
            fh.write(f"{silencer}ECHO OFF\n")
            fh.write(f"{silencer}SET PYTHONIOENCODING=utf-8\n")
            fh.write(f"{silencer}SET PYTHONUTF8=1\n")
            fh.write(
                f'{silencer}FOR /F "tokens=2 delims=:." %%A in (\'chcp\') do for %%B in (%%A) do set "_CONDA_OLD_CHCP=%%B"\n'
            )
            fh.write(f"{silencer}chcp 65001 > NUL\n")
            if dev_mode:
                from . import CONDA_SOURCE_ROOT

                fh.write(f"{silencer}SET CONDA_DEV=1\n")
                # In dev mode, conda is really:
                # 'python -m conda'
                # *with* PYTHONPATH set.
                fh.write(f"{silencer}SET PYTHONPATH={CONDA_SOURCE_ROOT}\n")
                fh.write(f"{silencer}SET CONDA_EXE={sys.executable}\n")
                fh.write(f"{silencer}SET _CE_M=-m\n")
                fh.write(f"{silencer}SET _CE_CONDA=conda\n")
            if debug_wrapper_scripts:
                fh.write("echo *** environment before *** 1>&2\n")
                fh.write("SET 1>&2\n")
            # Not sure there is any point in backing this up, nothing will get called with it reset
            # after all!
            # fh.write("@FOR /F \"tokens=100\" %%F IN ('chcp') DO @SET CONDA_OLD_CHCP=%%F\n")
            # fh.write('@chcp 65001>NUL\n')
            fh.write(f'{silencer}CALL "{conda_bat}" activate "{prefix}"\n')
            fh.write(f"{silencer}IF %ERRORLEVEL% NEQ 0 EXIT /b %ERRORLEVEL%\n")
            if debug_wrapper_scripts:
                fh.write("echo *** environment after *** 1>&2\n")
                fh.write("SET 1>&2\n")
            if multiline:
                # No point silencing the first line. If that's what's wanted then
                # it needs doing for each line and the caller may as well do that.
                fh.write(f"{arguments[0]}\n")
            else:
                assert not any("\n" in arg for arg in arguments), (
                    "Support for scripts where arguments contain newlines not implemented.\n"
                    ".. requires writing the script to an external file and knowing how to "
                    "transform the command-line (e.g. `python -c args` => `python file`) "
                    "in a tool dependent way, or attempting something like:\n"
                    ".. https://stackoverflow.com/a/15032476 (adds unacceptable escaping"
                    "requirements)"
                )
                fh.write(f"{silencer}{quote_for_shell(*arguments)}\n")
            fh.write(f"{silencer}IF %ERRORLEVEL% NEQ 0 EXIT /b %ERRORLEVEL%\n")
            fh.write(f"{silencer}chcp %_CONDA_OLD_CHCP%>NUL\n")
            script_caller = fh.name
        command_args = [comspec, "/d", "/c", script_caller]
    else:
        shell_path = which("bash") or which("sh")
        if shell_path is None:
            raise Exception("No compatible shell found!")

        # During tests, we sometimes like to have a temp env with e.g. an old python in it
        # and have it run tests against the very latest development sources. For that to
        # work we need extra smarts here, we want it to be instead:
        if dev_mode:
            conda_exe = [abspath(join(root_prefix, "bin", "python")), "-m", "conda"]
            dev_arg = "--dev"
            dev_args = [dev_arg]
        else:
            conda_exe = [
                environ.get("CONDA_EXE", abspath(join(root_prefix, "bin", "conda")))
            ]
            dev_arg = ""
            dev_args = []
        with Utf8NamedTemporaryFile(mode="w", prefix=tmp_prefix, delete=False) as fh:
            if dev_mode:
                from . import CONDA_SOURCE_ROOT

                fh.write(">&2 export PYTHONPATH=" + CONDA_SOURCE_ROOT + "\n")
            hook_quoted = quote_for_shell(*conda_exe, "shell.posix", "hook", *dev_args)
            if debug_wrapper_scripts:
                fh.write(">&2 echo '*** environment before ***'\n>&2 env\n")
                fh.write(f'>&2 echo "$({hook_quoted})"\n')
            fh.write(f'eval "$({hook_quoted})"\n')
            fh.write(f"conda activate {dev_arg} {quote_for_shell(prefix)}\n")
            if debug_wrapper_scripts:
                fh.write(">&2 echo '*** environment after ***'\n>&2 env\n")
            if multiline:
                # The ' '.join() is pointless since mutliline is only True when there's 1 arg
                # still, if that were to change this would prevent breakage.
                fh.write("{}\n".format(" ".join(arguments)))
            else:
                fh.write(f"{quote_for_shell(*arguments)}\n")
            script_caller = fh.name
        if debug_wrapper_scripts:
            command_args = [shell_path, "-x", script_caller]
        else:
            command_args = [shell_path, script_caller]

    return script_caller, command_args


def get_comspec():
    """Returns COMSPEC from envvars.

    Ensures COMSPEC envvar is set to cmd.exe, if not attempt to find it.

    :raises KeyError: COMSPEC is undefined and cannot be found.
    :returns: COMSPEC value.
    :rtype: str
    """
    if basename(environ.get("COMSPEC", "")).lower() != "cmd.exe":
        for comspec in (
            # %SystemRoot%\System32\cmd.exe
            environ.get("SystemRoot")
            and join(environ["SystemRoot"], "System32", "cmd.exe"),
            # %windir%\System32\cmd.exe
            environ.get("windir") and join(environ["windir"], "System32", "cmd.exe"),
        ):
            if comspec and isfile(comspec):
                environ["COMSPEC"] = comspec
                break
        else:
            log.warning(
                "cmd.exe could not be found. Looked in SystemRoot and windir env vars.\n"
            )

    # fails with KeyError if still undefined
    return environ["COMSPEC"]


def ensure_dir_exists(func):
    """
    Ensures that the directory exists for functions returning
    a Path object containing a directory
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)

        if isinstance(result, Path):
            try:
                result.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise CondaError(
                    "Error encountered while attempting to create cache directory."
                    f"\n  Directory: {result}"
                    f"\n  Exception: {exc}"
                )

        return result

    return wrapper
