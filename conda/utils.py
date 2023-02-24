# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache, wraps
from io import StringIO
import logging
from os.path import abspath, join, isfile, basename, dirname
from os import environ, PathLike
from pathlib import Path
import re
import sys

from . import CondaError
from .auxlib.compat import shlex_split_unicode, Utf8NamedTemporaryFile
from .common.compat import on_win, isiterable
from .common.path import win_path_to_unix, which
from .common.url import path_to_url
from .deprecations import deprecated
from .gateways.disk.read import compute_sum


log = logging.getLogger(__name__)

def path_identity(path):
    """Used as a dummy path converter where no conversion necessary"""
    return path


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
            group[len(root_prefix) + 1], group[len(root_prefix) + 2:].replace("/", "\\")
        )

    translation = re.sub(path_re, _translation, path)
    translation = re.sub(":([a-zA-Z]):\\\\",
                         lambda match: ";" + match.group(0)[1] + ":\\",
                         translation)
    return translation


# curry cygwin functions
def win_path_to_cygwin(path):
    return win_path_to_unix(path, "/cygdrive")


def cygwin_path_to_win(path):
    return unix_path_to_win(path, "/cygdrive")


def translate_stream(stream, translator):
    return "\n".join(translator(line) for line in stream.split("\n"))


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
        return '%d B' % n
    k = n/1024
    if k < 1024:
        return '%d KB' % round(k)
    m = k/1024
    if m < 1024:
        return '%.1f MB' % m
    g = m/1024
    return '%.2f GB' % g


# TODO: this should be done in a more extensible way
#     (like files for each shell, with some registration mechanism.)

# defaults for unix shells.  Note: missing "exe" entry, which should be set to
#    either an executable on PATH, or a full path to an executable for a shell
unix_shell_base = dict(
    binpath="/bin/",  # mind the trailing slash.
    debug_args=["-x"],
    echo="echo",
    env_script_suffix=".sh",
    exec="exec",
    line_join=" && ",
    nul="2>/dev/null",
    path_from=path_identity,
    path_to=path_identity,
    pathsep=":",
    printdefaultenv="echo $CONDA_DEFAULT_ENV",
    printpath="echo $PATH",
    printps1="echo $CONDA_PROMPT_MODIFIER",
    promptvar="PS1",
    sep="/",
    set_var="export ",
    script_args=[],
    shell_args=["-l", "-c"],
    shell_suffix=".sh",
    slash_convert=("\\", "/"),
    source_setup="source",
    test_echo_extra="",
    var_format="${}",
)

msys2_shell_base = dict(
    unix_shell_base,
    path_from=unix_path_to_win,
    path_to=win_path_to_unix,
    binpath="/bin/",  # mind the trailing slash.
    printpath="python -c \"import os; print(';'.join(os.environ['PATH'].split(';')[1:]))\" | cygpath --path -f -",  # NOQA
)

if on_win:
    shells = {
        # "powershell.exe": dict(
        #    echo="echo",
        #    test_echo_extra=" .",
        #    var_format="${var}",
        #    binpath="/bin/",  # mind the trailing slash.
        #    source_setup="source",
        #    nul='2>/dev/null',
        #    set_var='export ',
        #    shell_suffix=".ps",
        #    env_script_suffix=".ps",
        #    debug_args=[],
        #    script_args=[],
        #    shell_args=[],
        #    printps1='echo $PS1',
        #    printdefaultenv='echo $CONDA_DEFAULT_ENV',
        #    printpath="echo %PATH%",
        #    exe="powershell.exe",
        #    path_from=path_identity,
        #    path_to=path_identity,
        #    slash_convert = ("/", "\\"),
        # ),
        "cmd.exe": dict(
            echo="@echo",
            var_format="%{}%",
            binpath="\\Scripts\\",  # mind the trailing slash.
            source_setup="call",
            test_echo_extra="",
            nul='1>NUL 2>&1',
            set_var='set ',
            shell_suffix=".bat",
            env_script_suffix=".bat",
            printps1="@echo %PROMPT%",
            promptvar="PROMPT",
            # parens mismatched intentionally.  See http://stackoverflow.com/questions/20691060/how-do-i-echo-a-blank-empty-line-to-the-console-from-a-windows-batch-file # NOQA
            printdefaultenv='IF NOT "%CONDA_DEFAULT_ENV%" == "" (\n'
                            'echo %CONDA_DEFAULT_ENV% ) ELSE (\n'
                            'echo()',
            printpath="@echo %PATH%",
            exe="cmd.exe",
            script_args=["/d", "/c"],
            shell_args=["/d", "/c"],
            debug_args=[],
            exec='',
            path_from=path_identity,
            path_to=path_identity,
            slash_convert=("/", "\\"),
            sep="\\",
            pathsep=";",
        ),
        "cygwin": dict(
            unix_shell_base,
            exe="bash.exe",
            binpath="/Scripts/",  # mind the trailing slash.
            path_from=cygwin_path_to_win,
            path_to=win_path_to_cygwin
        ),
        # bash is whichever bash is on PATH.  If using Cygwin, you should use the cygwin
        #    entry instead.  The only major difference is that it handle's cygwin's /cygdrive
        #    filesystem root.
        "bash.exe": dict(
            msys2_shell_base, exe="bash.exe",
        ),
        "bash": dict(
            msys2_shell_base, exe="bash",
        ),
        "sh.exe": dict(
            msys2_shell_base, exe="sh.exe",
        ),
        "zsh.exe": dict(
            msys2_shell_base, exe="zsh.exe",
        ),
        "zsh": dict(
            msys2_shell_base, exe="zsh",
        ),
    }

else:
    shells = {
        "bash": dict(
            unix_shell_base, exe="bash",
        ),
        "dash": dict(
            unix_shell_base, exe="dash",
            source_setup=".",
        ),
        "zsh": dict(
            unix_shell_base, exe="zsh",
        ),
        "fish": dict(
            unix_shell_base, exe="fish",
            pathsep=" ",
            debug_args=["--debug='complete,*history*'"],
        ),
        "sh": dict(  # fallback to sh if no bash (#8611)
            unix_shell_base,
            exe="sh",
            shell_args=["-c"],  # -l not supported in POSIX sh
        ),
    }


# ##########################################
# put back because of conda build
# ##########################################

urlpath = url_path = path_to_url


@deprecated(
    "23.9",
    "24.3",
    addendum='Use `conda.gateways.disk.read.compute_sum(path, "md5")` instead.',
)
def md5_file(path: str | PathLike) -> str:
    return compute_sum(path, "md5")


@deprecated("23.9", "24.3", addendum="Use `conda.gateways.disk.read.compute_sum` instead.")
def hashsum_file(path: str | PathLike, mode: Literal["md5", "sha256"] = "md5") -> str:
    return compute_sum(path, mode)


@lru_cache(maxsize=None)
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
    try:
        from shlex import join as _args_join
    except ImportError:
        # [backport] Python <3.8
        def _args_join(args):
            """Return a shell-escaped string from *args*."""
            from shlex import quote

            return " ".join(quote(arg) for arg in args)


# Ensures arguments are a tuple or a list. Strings are converted
# by shlex_split_unicode() which is bad; we warn about it or else
# we assert (and fix the code).
def massage_arguments(arguments, errors='assert'):

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
        if errors == 'assert':
            # This should be something like 'conda programming bug', it is an assert
            assert False, 'Please ensure arguments are not strings'
        else:
            arguments = shlex_split_unicode(arguments)
            log.warning("Please ensure arguments is not a string; "
                        "used `shlex_split_unicode()` on it")

    if not isiterable(arguments):
        arguments = (arguments,)

    assert not any([isiterable(arg) for arg in arguments]), "Individual arguments must not be iterable"  # NOQA
    arguments = list(arguments)

    return arguments


def _wrap_bat(
        root_prefix,
        prefix,
        dev_mode,
        debug_wrapper_scripts,
        arguments,
):
    """wrap :param arguments: in a .bat file"""
    with StringIO() as bat:
        if dev_mode:
            from conda import CONDA_PACKAGE_ROOT
            conda_bat = join(CONDA_PACKAGE_ROOT, 'shell', 'condabin', 'conda.bat')
        else:
            conda_bat = environ.get("CONDA_BAT",
                                    abspath(join(root_prefix, 'condabin', 'conda.bat')))
        silencer = "" if debug_wrapper_scripts else "@"
        bat.write(f"{silencer}ECHO OFF\n")
        bat.write(f"{silencer}SET PYTHONIOENCODING=utf-8\n")
        bat.write(f"{silencer}SET PYTHONUTF8=1\n")
        bat.write(
            f'{silencer}FOR /F "tokens=2 delims=:." %%A in (\'chcp\') do for %%B in (%%A) do set "_CONDA_OLD_CHCP=%%B"\n'  # noqa
        )
        bat.write(f"{silencer}chcp 65001 > NUL\n")
        if dev_mode:
            from . import CONDA_SOURCE_ROOT

            bat.write(f"{silencer}SET CONDA_DEV=1\n")
            # In dev mode, conda is really:
            # 'python -m conda'
            # *with* PYTHONPATH set.
            bat.write(f"{silencer}SET PYTHONPATH={CONDA_SOURCE_ROOT}\n")
            bat.write(f"{silencer}SET CONDA_EXE={sys.executable}\n")
            bat.write(f"{silencer}SET _CE_M=-m\n")
            bat.write(f"{silencer}SET _CE_CONDA=conda\n")
        if debug_wrapper_scripts:
            bat.write("echo *** environment before *** 1>&2\n")
            bat.write("SET 1>&2\n")
        # Not sure there is any point in backing this up, nothing will get called with it reset
        # after all!
        # fh.write("@FOR /F \"tokens=100\" %%F IN ('chcp') DO @SET CONDA_OLD_CHCP=%%F\n")
        # fh.write('@chcp 65001>NUL\n')
        bat.write(f'{silencer}CALL "{conda_bat}" activate "{prefix}"\n')
        bat.write(f"{silencer}IF %ERRORLEVEL% NEQ 0 EXIT /b %ERRORLEVEL%\n")
        if debug_wrapper_scripts:
            bat.write("echo *** environment after *** 1>&2\n")
            bat.write("SET 1>&2\n")
        if len(arguments) == 1 and "\n" in arguments[0]:  # multiline
            # No point silencing the first line. If that's what's wanted then
            # it needs doing for each line and the caller may as well do that.
            bat.write(f"{arguments[0]}\n")
        else:
            assert not any("\n" in arg for arg in arguments), (
                "Support for scripts where arguments contain newlines not implemented.\n"
                ".. requires writing the script to an external file and knowing how to "
                "transform the command-line (e.g. `python -c args` => `python file`) "
                "in a tool dependent way, or attempting something like:\n"
                ".. https://stackoverflow.com/a/15032476 (adds unacceptable escaping"
                "requirements)"
            )
            bat.write(f"{silencer}{quote_for_shell(*arguments)}\n")
        bat.write(f"{silencer}IF %ERRORLEVEL% NEQ 0 EXIT /b %ERRORLEVEL%\n")
        bat.write(f"{silencer}chcp %_CONDA_OLD_CHCP%>NUL\n")
        return bat.getvalue()


def _wrap_sh(
    root_prefix,
    prefix,
    dev_mode,
    debug_wrapper_scripts,
    arguments,
):
    """wrap :param arguments: in a .sh script"""
    with StringIO() as sh:
        if dev_mode:
            from . import CONDA_SOURCE_ROOT

            sh.write(">&2 export PYTHONPATH=" + CONDA_SOURCE_ROOT + "\n")
            conda_exe = [abspath(join(root_prefix, 'bin', 'python')), '-m', 'conda']
            dev_arg = '--dev'
            dev_args = [dev_arg]
        else:
            conda_exe = [environ.get("CONDA_EXE", abspath(join(root_prefix, 'bin', 'conda')))]
            dev_arg = ''
            dev_args = []
        hook_quoted = quote_for_shell(*conda_exe, "shell.posix", "hook", *dev_args)
        if debug_wrapper_scripts:
            sh.write(">&2 echo '*** environment before ***'\n" ">&2 env\n")
            sh.write(f'>&2 echo "$({hook_quoted})"\n')
        sh.write(f'eval "$({hook_quoted})"\n')
        sh.write(f"conda activate {dev_arg} {quote_for_shell(prefix)}\n")
        if debug_wrapper_scripts:
            sh.write(">&2 echo '*** environment after ***'\n" ">&2 env\n")
        if len(arguments) == 1 and "\n" in arguments[0]:  # multiline
            # The ' '.join() is pointless since mutliline is only True when there's 1 arg
            # still, if that were to change this would prevent breakage.
            sh.write("{}\n".format(" ".join(arguments)))
        else:
            sh.write(f"{quote_for_shell(*arguments)}\n")
        return sh.getvalue()


def _get_shell(shell_name=None, condition=lambda x: True):
    """
    get a compatible shell's configuration dict

    :param shell_name: (optional str) name of a shell
            if None, iterate through global "shells" and return first match
    :param condition: (optional callable[[dict],bool]) matching condition
            should return True when passed a shell configuration dict
            if that shell is acceptable, False to continue searching
    """
    shell = {}
    # use first matching shell if shell_name is None
    for s in [shell_name] if shell_name else shells.keys():
        scfg = shells.get(s, {})
        if which(scfg.get("exe", "")) and condition(scfg):
            shell = scfg.copy()
            if shell["exe"] == "cmd.exe":
                shell["which"] = get_comspec()
            else:
                shell["which"] = which(shell["exe"])
            break
    if not shell:
        raise RuntimeError("No compatible shell found!")
    return shell


def wrap_subprocess_call(
    root_prefix,
    prefix,
    dev_mode,
    debug_wrapper_scripts,
    arguments,
    use_system_tmp_path=False,
):
    """
    :return: (script_caller, command_args)
        - script_caller: filename of the temporary script
        - command_args: full list of args, including script_caller,
                        to pass to the subprocess
    """
    arguments = massage_arguments(arguments)
    if not use_system_tmp_path:
        tmp_prefix = abspath(join(prefix, ".tmp"))
    else:
        tmp_prefix = None
    script_caller = None
    shell = _get_shell(condition=lambda s: s["shell_suffix"] in [".bat", ".sh"])
    with Utf8NamedTemporaryFile(
        mode="w", prefix=tmp_prefix, suffix=shell["shell_suffix"], delete=False
    ) as fh:
        if shell["shell_suffix"] == ".sh":
            fh.write(_wrap_sh(root_prefix, prefix, dev_mode, debug_wrapper_scripts, arguments))
        elif shell["shell_suffix"] == ".bat":
            fh.write(_wrap_bat(root_prefix, prefix, dev_mode, debug_wrapper_scripts, arguments))
        else:
            raise ValueError(f"cannot wrap commands in '{shell['shell_suffix']}' script")
        script_caller = fh.name
    command_args = [
        shell["which"],
        *(shell["debug_args"] if debug_wrapper_scripts else []),
        *shell["script_args"],
        script_caller,
    ]
    return script_caller, command_args


def wrap_exec_call(
        root_prefix,
        prefix,
        dev_mode,
        debug_wrapper_scripts,
        arguments,
):
    """
    :return: (script, command_args)
        - script: contents of the wrapper script
        - command_args: full list of args, including contents of script, to exec
    """
    arguments = massage_arguments(arguments)
    shell = _get_shell(condition=lambda s: s["shell_suffix"] in [".bat", ".sh"])
    if shell["exec"]:
        arguments.insert(0, shell["exec"])
    if shell["shell_suffix"] == ".sh":
        script = _wrap_sh(root_prefix, prefix, dev_mode, debug_wrapper_scripts, arguments)
    elif shell["shell_suffix"] == ".bat":
        script = _wrap_bat(root_prefix, prefix, dev_mode, debug_wrapper_scripts, arguments)
    else:
        raise ValueError(f"cannot wrap commands in '{shell['shell_suffix']}' script")
    if shell.get("line_join"):
        # join lines with shell['line_join'], dropping empty lines
        command = shell["line_join"].join(line for line in script.splitlines() if line)
    else:
        command = script
    command_args = [
        shell["which"],
        *(shell["debug_args"] if debug_wrapper_scripts else []),
        *shell["shell_args"],
        command,
    ]
    return script, command_args


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
            environ.get("SystemRoot") and join(environ["SystemRoot"], "System32", "cmd.exe"),
            # %windir%\System32\cmd.exe
            environ.get("windir") and join(environ["windir"], "System32", "cmd.exe"),
        ):
            if comspec and isfile(comspec):
                environ["COMSPEC"] = comspec
                break
        else:
            log.warn("cmd.exe could not be found. Looked in SystemRoot and windir env vars.\n")

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


@deprecated("23.9", "24.3", addendum="Use `open` instead.")
@contextmanager
def safe_open(*args, **kwargs):
    """
    Allows us to open files while catching any exceptions
    and raise them as CondaErrors instead.

    We do this to provide a more informative/actionable error output.
    """
    try:
        fp = open(*args, **kwargs)
        yield fp
    except OSError as exc:
        raise CondaError(
            "Error encountered while reading or writing from cache."
            f"\n  File: {args[0]}"
            f"\n  Exception: {exc}"
        )

    fp.close()
