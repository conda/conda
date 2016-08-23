from __future__ import absolute_import, division, print_function

import collections
import hashlib
import logging
import re
import sys
import threading
from functools import partial

from .common.url import path_to_url

log = logging.getLogger(__name__)

on_win = bool(sys.platform == "win32")


class memoized(object):
    """Decorator. Caches a function's return value each time it is called.
    If called later with the same arguments, the cached value is returned
    (not reevaluated).
    """
    def __init__(self, func):
        self.func = func
        self.cache = {}
        self.lock = threading.Lock()

    def __call__(self, *args, **kw):
        newargs = []
        for arg in args:
            if isinstance(arg, list):
                newargs.append(tuple(arg))
            elif not isinstance(arg, collections.Hashable):
                # uncacheable. a list, for instance.
                # better to not cache than blow up.
                return self.func(*args, **kw)
            else:
                newargs.append(arg)
        newargs = tuple(newargs)
        key = (newargs, frozenset(sorted(kw.items())))
        with self.lock:
            if key in self.cache:
                return self.cache[key]
            else:
                value = self.func(*args, **kw)
                self.cache[key] = value
                return value


# For instance methods only
class memoize(object):  # 577452
    def __init__(self, func):
        self.func = func

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self.func
        return partial(self, obj)

    def __call__(self, *args, **kw):
        obj = args[0]
        try:
            cache = obj.__cache
        except AttributeError:
            cache = obj.__cache = {}
        key = (self.func, args[1:], frozenset(sorted(kw.items())))
        try:
            res = cache[key]
        except KeyError:
            res = cache[key] = self.func(*args, **kw)
        return res

@memoized
def gnu_get_libc_version():
    """
    If on linux, get installed version of glibc, otherwise return None
    """

    if not sys.platform.startswith('linux'):
        return None

    from ctypes import CDLL, cdll, c_char_p

    cdll.LoadLibrary('libc.so.6')
    libc = CDLL('libc.so.6')
    f = libc.gnu_get_libc_version
    f.restype = c_char_p
    return f()


def hashsum_file(path, mode='md5'):
    h = hashlib.new(mode)
    with open(path, 'rb') as fi:
        while True:
            chunk = fi.read(262144)  # process chunks of 256KB
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def md5_file(path):
    return hashsum_file(path, 'md5')


def path_identity(path):
    """Used as a dummy path converter where no conversion necessary"""
    return path


def win_path_to_unix(path, root_prefix=""):
    """Convert a path or ;-separated string of paths into a unix representation

    Does not add cygdrive.  If you need that, set root_prefix to "/cygdrive"
    """
    path_re = '(?<![:/^a-zA-Z])([a-zA-Z]:[\/\\\\]+(?:[^:*?"<>|]+[\/\\\\]+)*[^:*?"<>|;\/\\\\]+?(?![a-zA-Z]:))'  # noqa

    def _translation(found_path):
        found = found_path.group(1).replace("\\", "/").replace(":", "").replace("//", "/")
        return root_prefix + "/" + found
    path = re.sub(path_re, _translation, path).replace(";/", ":/")
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
        return "{0}:{1}".format(group[len(root_prefix)+1],
                                group[len(root_prefix)+2:].replace("/", "\\"))
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
                       echo="echo",
                       env_script_suffix=".sh",
                       nul='2>/dev/null',
                       path_from=path_identity,
                       path_to=path_identity,
                       pathsep=":",
                       printdefaultenv='echo "${CONDA_DEFAULT_ENV}"',
                       printpath='echo "${PATH}"',
                       printps1='echo "${PS1}"',
                       promptvar='PS1',
                       sep="/",
                       setenvvar='export {variable}="{value}"',
                       unsetenvvar='unset {variable}',
                       setvar='{variable}="{value}"',
                       unsetvar='unset {variable}',
                       shell_args=["-l", "-c"],
                       shell_suffix="",
                       slash_convert=("\\", "/"),
                       source=".",
                       test_echo_extra="",
                       var_format="${}",
)

msys2_shell_base = dict(
                        unix_shell_base,
                        path_from=unix_path_to_win,
                        path_to=win_path_to_unix,
                        binpath="/Scripts/",  # mind the trailing slash.
)

if on_win:
    shells = {
        # "powershell.exe": dict(
        #    echo="echo",
        #    test_echo_extra=" .",
        #    var_format="${var}",
        #    binpath="/bin/",  # mind the trailing slash.
        #    source="source",
        #    nul='2>/dev/null',
        #    setenvvar='export {variable}="{value}"',
        #    shell_suffix=".ps",
        #    env_script_suffix=".ps",
        #    printps1='echo "${PS1}"',
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
            source="call",
            test_echo_extra="",
            nul='1>NUL 2>&1',
            setvar='set {variable}="{value}"',
            unsetvar='set {variable}=',
            setenvvar='set {variable}="{value}"',
            unsetenvvar='set {variable}=',
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
            shell_args=["/d", "/c"],
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
    c_shell_base = dict(
                        unix_shell_base,
                        env_script_suffix=".csh",
                        nul='>&/dev/null',
                        printps1='echo "${prompt}"',
                        promptvar='prompt',
                        setenvvar='setenv {variable} "{value}"',
                        unsetenvvar='unsetenv {variable}',
                        setvar='set {variable}="{value}"',
                        unsetvar='unset {variable}',
                        shell_args=["-c"],
                        source="source",

    )
    shells = {
        "bash": dict(
            unix_shell_base, exe="bash",
                    ),
        "zsh": dict(
            unix_shell_base, exe="zsh",
                   ),
        "dash": dict(
            unix_shell_base, exe="dash",
                   ),
        "posh": dict(
            unix_shell_base, exe="posh",
                   ),
        "fish": dict(
            unix_shell_base, exe="fish",
            pathsep=" ",
                    ),
        "sh": dict(
            unix_shell_base, exe="sh",
                    ),
        "csh": dict(
            c_shell_base, exe="csh",
                    ),
        "tcsh": dict(
            c_shell_base, exe="tcsh",
                    ),
    }

# put back because of conda build
urlpath = url_path = path_to_url
