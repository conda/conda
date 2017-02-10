from __future__ import absolute_import, division, print_function, unicode_literals

import collections
from functools import partial
import hashlib
import logging
from os.path import dirname
import re
import sys
from textwrap import dedent
import threading

from .common.compat import on_win
from .common.url import path_to_url

log = logging.getLogger(__name__)


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

    result = f()
    if hasattr(result, 'decode'):
        result = result.decode('utf-8')
    return result


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

    path_re = root_prefix + r'/([a-zA-Z])(/(?:(?![:\s]/)[^:*?"<>])*)'

    def _translation(found_path):
        return "{0}:{1}".format(found_path.group(1),
                                found_path.group(2).replace("/", "\\"))

    path = re.sub(path_re, _translation, path)
    path = re.sub(r':([a-zA-Z]):\\', r';\1:\\', path)

    return path


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
#
# remember the exe fields are exclusively used to call the correct
# executable for the unittesting, hence why some of the Windows paths
# are absolutes
posix_bash_base = dict(
    allargs='${@}',
    binpath='/bin/',  # mind the trailing slash.
    defaultenv_print='echo "${CONDA_DEFAULT_ENV}"',
    echo='echo',
    envvar_getall='env',
    envvar_set='export {variable}="{value}"',
    envvar_unset='unset {variable}',
    flag_double='--',
    flag_single='-',
    nul='2>/dev/null',
    path_delim=':',
    path_from=path_identity,
    path_print='echo "${PATH}"',
    path_to=path_identity,
    path_prepend='export PATH="{}:${{PATH}}"',
    prompt_print='echo "${PS1}"',
    prompt_set='export PS1="{value}"',
    prompt_unset='unset PS1',
    sep='/',
    shell_args='-l',
    source='. "{}"',
    suffix_executable='',
    suffix_script='.sh',
    var_format='${}',
    var_set='{variable}="{value}"',
    var_unset='unset {variable}',
)
posix_c_base = dict(
    posix_bash_base,
    # exe=,
    allargs='${argv}',
    envvar_set='setenv {variable} "{value}"',
    envvar_unset='unsetenv {variable}',
    nul='>&/dev/null',
    path_prepend=dedent("""\
        set path=({0} ${{path}})
        set PATH=({0}:${{PATH}})"""),
    prompt_print='echo "${prompt}"',
    prompt_set='set prompt="{value}"',
    prompt_unset='unset prompt',
    shell_args='',
    source='source "{}"',
    suffix_executable='',
    suffix_script='.csh',
    var_set='set {variable}="{value}"',
)

cygwin_prefix = "C:\\cygwin64\\bin\\"
cygwin_bash_base = dict(
    posix_bash_base,
    # this is the path that needs to be added to PATH just before entering
    # Cygwin shell such that we can find our executables
    pathprefix=cygwin_prefix,
    binpath='/Scripts/',  # mind the trailing slash.
    envvar_unset='[ -n "${{{variable}+x}}" ] && unset {variable}',
    path_from=cygwin_path_to_win,
    path_to=win_path_to_cygwin,
    var_unset='[ -n "${{{variable}+x}}" ] && unset {variable}',
)

mingw_prefix = "C:\\MinGW\\msys\\1.0\\bin\\"
mingw_bash_base = dict(
    posix_bash_base,
    # this is the path that needs to be added to PATH just before entering
    # MinGW shell such that we can find our executables
    pathprefix=mingw_prefix + ";C:\\MinGW\\MSYS\\1.0\\local\\bin;C:\\MinGW\\bin",
    binpath='/Scripts/',  # mind the trailing slash.
    path_from=unix_path_to_win,
    path_to=win_path_to_unix,
)

msys_prefix = "C:\\msys64\\usr\\bin\\"
msys_bash_base = dict(
    posix_bash_base,
    # this is the path that needs to be added to PATH just before entering
    # MSYS2 shell such that we can find our executables
    pathprefix=msys_prefix,
    binpath='/Scripts/',  # mind the trailing slash.
    path_from=unix_path_to_win,
    path_to=win_path_to_unix,
    shell_args='',
)
msys_c_base = dict(
    posix_c_base,
    # this is the path that needs to be added to PATH just before entering
    # MSYS2 shell such that we can find our executables
    pathprefix=msys_prefix,
    binpath='/Scripts/',  # mind the trailing slash.
    path_from=unix_path_to_win,
    path_to=win_path_to_unix,
    shell_args='',
)

batch_base = dict(
    binpath='\\Scripts\\',  # mind the trailing slash.
    # parenthesis mismatched intentionally
    # see http://stackoverflow.com/questions/20691060/
    #   how-do-i-echo-a-blank-empty-line-to-the-console-from-a-windows-batch-file
    # NOQA
    defaultenv_print=dedent('''\
        @IF /I NOT "%CONDA_DEFAULT_ENV%"=="" (
            @ECHO %CONDA_DEFAULT_ENV%
        ) ELSE (
            @ECHO(
        )'''),
    echo='@ECHO',
    envvar_getall='@SET',
    envvar_set='@SET "{variable}={value}"',
    envvar_unset='@SET {variable}=',
    flag_double='/',
    flag_single='/',
    nul='1>NUL 2>&1',
    path_delim=';',
    path_from=path_identity,
    path_print='@ECHO %PATH%',
    path_to=path_identity,
    path_prepend='@SET "PATH={};%PATH%"',
    prompt_print='@ECHO %PROMPT%',
    prompt_set='@SET "PROMPT={value}"',
    prompt_unset='@SET PROMPT=',
    sep='\\',
    shell_args='/d /c',
    source='@CALL "{}"',
    suffix_executable='.bat',
    suffix_script='.bat',
    var_format='%{}%',
    var_set='@SET "{variable}={value}"',
    var_unset='@SET {variable}=',
)
powershell_base = dict(
    posix_bash_base,
    binpath='\Scripts\\',  # mind the trailing slash.
    defaultenv_print='echo "${env:CONDA_DEFAULT_ENV}"',
    envvar_getall=dedent('''\
        Get-ChildItem env: | % {
        $name=$_.Name
        $value=$_.Value
        echo "$name=$value"
        }'''),
    envvar_set='$env:{variable}="{value}"',
    envvar_unset='$env:{variable}=""',
    path_delim=';',
    path_print='echo ${env:Path}',
    path_prepend='$env:PATH="{};${{env:PATH}}"',
    prompt_print='(Get-Command Prompt).definition',
    prompt_set=dedent('''\
        function Prompt {{
            return "{value}";
        }}'''),
    prompt_unset=dedent('''\
        function Prompt {
            return "";
        }'''),
    sep='\\',
    shell_args='-File',
    source='{}',
    suffix_executable='.ps1',
    suffix_script='.ps1',
    var_set='${variable}="{value}"',
    var_unset='Remove-Variable {variable}',
)

if on_win:
    shells = {
        "powershell.exe": dict(
            powershell_base,
            exe='powershell.exe',
        ),
        "cmd.exe": dict(
            batch_base,
            exe='cmd.exe',
        ),
        "bash.cygwin": dict(
            cygwin_bash_base,
            # this is the default install location for Cygwin
            exe=cygwin_prefix + 'bash.exe',
        ),
        "bash.mingw": dict(
            mingw_bash_base,
            # this is the default install location for MinGW
            exe=mingw_prefix + 'bash.exe',
        ),
        "bash.msys": dict(
            msys_bash_base,
            # this is the default install location for MSYS
            exe=msys_prefix + 'bash.exe',
        ),
        "dash.msys": dict(
            msys_bash_base,
            # this is the default install location for MSYS
            exe=msys_prefix + 'dash.exe',
        ),
        "zsh.msys": dict(
            msys_bash_base,
            # this is the default install location for MSYS
            exe=msys_prefix + 'zsh.exe',
        ),
        "ksh.msys": dict(
            msys_bash_base,
            # this is the default install location for MSYS
            exe=msys_prefix + 'ksh.exe',
        ),
        "csh.msys": dict(
            msys_c_base,
            # this is the default install location for MSYS
            exe=msys_prefix + 'csh.exe',
        ),
        "tcsh.msys": dict(
            msys_c_base,
            # this is the default install location for MSYS
            exe=msys_prefix + 'tcsh.exe',
        ),
    }

else:
    shells = {
        "bash": dict(
            posix_bash_base,
            exe='bash',
        ),
        "zsh": dict(
            posix_bash_base,
            exe='zsh',
        ),
        "dash": dict(
            posix_bash_base,
            exe='dash',
            shell_args='',
        ),
        "posh": dict(
            posix_bash_base,
            exe='posh',
        ),
        "ksh": dict(
            posix_bash_base,
            exe='ksh',
            shell_args='',
        ),
        "fish": dict(
            posix_bash_base,
            exe='fish',
            path_delim=' ',
        ),
        "sh": dict(
            posix_bash_base,
            exe='sh',
        ),
        "csh": dict(
            posix_c_base,
            exe='csh',
        ),
        "tcsh": dict(
            posix_c_base,
            exe='tcsh',
        ),
    }

# put back because of conda build
urlpath = url_path = path_to_url


@memoized
def sys_prefix_unfollowed():
    """Since conda is installed into non-root environments as a symlink only
    and because sys.prefix follows symlinks, this function can be used to
    get the 'unfollowed' sys.prefix.

    This value is usually the same as the prefix of the environment into
    which conda has been symlinked. An example of when this is necessary
    is when conda looks for external sub-commands in find_commands.py
    """
    try:
        frame = sys._current_frames().values()[0]
        while frame.f_back:
            frame = frame.f_back
        code = frame.f_code
        filename = code.co_filename
        unfollowed = dirname(dirname(filename))
    except:
        return sys.prefix
    return unfollowed
