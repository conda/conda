from __future__ import absolute_import, division, print_function, unicode_literals

import errno
import functools
import os
import re
import sys
from os.path import abspath, isdir
from textwrap import dedent

from ..common.compat import on_win, text_type
from ..exceptions import (CondaEnvironmentError, CondaHelp, CondaValueError, TooFewArgumentsError,
                          TooManyArgumentsError)
from ..utils import shells

# help dialog texts
WIN_ACTIVATE = dedent("""\
    Adds the 'Scripts' and 'Library\\bin' directories of the environment ENV to
    the front of PATH. ENV may either refer to just the name of the
    environment, or the full prefix path.""")
UNIX_ACTIVATE = dedent("""\
    Adds the 'bin' directory of the environment ENV to the front of PATH. ENV
    may either refer to just the name of the environment, or the full prefix
    path.""")
WIN_DEACTIVATE = dedent("""\
    Removes the 'Scripts' and 'Library\\bin' directories of the currently
    active environment from the front of PATH.""")
UNIX_DEACTIVATE = dedent("""\
    Removes the 'bin' directory of the currently active environment from the
    front of PATH.""")
HELP_ACTIVATE = dedent("""\
    {unknown}Usage: {command} [ENV] [{flag_single}h] [{flag_single}v]

    {blurb}

    Where:
        ENV             the virtual environment to activate (dflt: root)
        {flag_single}h,{flag_double:>2}help       shows this dialog
        {flag_single}v,{flag_double:>2}verbose    shows more detailed info for the activate process
                        (useful when there are post-activate scripts)

    Alternatively use the following variables when the above parameter passing
    doesn't work:
        {CONDA_ENVNAME}
        {CONDA_HELP}
        {CONDA_VERBOSE}

    Example(s):
        {command} root
        {CONDA_ENVNAME_root} ; {command}""")
HELP_DEACTIVATE = dedent("""\
    {unknown}Usage: {command} [{flag_single}h] [{flag_single}v]

    {blurb}

    Where:
        {flag_single}h,{flag_double:>2}help       shows this dialog
        {flag_single}v,{flag_double:>2}verbose    shows more detailed info for the activate process
                        (useful when there are pre-deactivate scripts)

    Alternatively use the following variables when the above parameter passing
    doesn't work:
        {CONDA_HELP}
        {CONDA_VERBOSE}

    Example(s):
        {command}""")

def help(mode, shell, unknown):
    kwargs = {
        "CONDA_ENVNAME":        shells[shell]["var_set"].format(
                                variable="CONDA_ENVNAME",
                                value="ENV"),
        "CONDA_ENVNAME_root":   shells[shell]["var_set"].format(
                                variable="CONDA_ENVNAME",
                                value="root"),
        "CONDA_HELP":           shells[shell]["var_set"].format(
                                variable="CONDA_HELP",
                                value="true"),
        "CONDA_VERBOSE":        shells[shell]["var_set"].format(
                                variable="CONDA_VERBOSE",
                                value="true"),
        "flag_single":          shells[shell]["flag_single"],
        "flag_double":          shells[shell]["flag_double"],
    }

    unknown = [u for u in unknown if not re.match(r'^\s*$', u)]
    if len(unknown) > 0:
        unknown = ("[{{program}}]: ERROR: "
                   "Unknown/Invalid flag/parameter ({unknown})\n").format(
                   unknown=" ".join(unknown))
        conda_exception = functools.partial(CondaHelp, returncode=1)
    else:
        unknown = ""
        conda_exception = functools.partial(CondaHelp, returncode=0)

    # mode will be ..checkenv in activate if an environment is already
    # activated
    if mode in ('..activate', '..checkenv'):
        unknown = unknown.format(program="ACTIVATE")

        if shell in ["cmd.exe", "powershell.exe"]:
            raise conda_exception(HELP_ACTIVATE.format(
                command='activate',
                unknown=unknown,
                blurb=WIN_ACTIVATE,
                **kwargs))

        elif shell in ["csh", "tcsh"]:
            raise conda_exception(HELP_ACTIVATE.format(
                command='source "`which activate`"',
                unknown=unknown,
                blurb=UNIX_ACTIVATE,
                **kwargs))
        else:
            raise conda_exception(HELP_ACTIVATE.format(
                command='. activate',
                unknown=unknown,
                blurb=UNIX_ACTIVATE,
                **kwargs))
    elif mode == '..deactivate':
        unknown = unknown.format(program="DEACTIVATE")

        if shell in ["cmd.exe", "powershell.exe"]:
            raise conda_exception(HELP_DEACTIVATE.format(
                command='deactivate',
                unknown=unknown,
                blurb=WIN_DEACTIVATE,
                **kwargs))
        elif shell in ["csh", "tcsh"]:
            raise conda_exception(HELP_DEACTIVATE.format(
                command='source "`which deactivate`"',
                unknown=unknown,
                blurb=UNIX_DEACTIVATE,
                **kwargs))
        else:
            raise conda_exception(HELP_DEACTIVATE.format(
                command='. deactivate',
                unknown=unknown,
                blurb=UNIX_DEACTIVATE,
                **kwargs))
    else:
        raise conda_exception("No help available for command {mode}".format(mode=mode))


def prefix_from_arg(arg, shelldict):
    from conda.base.context import context, locate_prefix_by_name
    'Returns a platform-native path'
    # MSYS2 converts Unix paths to Windows paths with unix seps
    # so we must check for the drive identifier too.
    if shelldict['sep'] in arg and not re.match('[a-zA-Z]:', arg):
        # strip is removing " marks, not \ - look carefully
        native_path = shelldict['path_from'](arg)
        if isdir(abspath(native_path.strip("\""))):
            prefix = abspath(native_path.strip("\""))
        else:
            raise CondaValueError('Could not find environment: {env}'.format(env=native_path))
    else:
        prefix = locate_prefix_by_name(context, arg.replace('/', os.path.sep))
    return prefix


def binpath_from_arg(arg, shelldict):
    # prefix comes back as platform-native path
    prefix = prefix_from_arg(arg, shelldict=shelldict)
    if on_win:
        paths = [
            prefix.rstrip("\\"),
            os.path.join(prefix, 'Library', 'mingw-w64', 'bin'),
            os.path.join(prefix, 'Library', 'usr', 'bin'),
            os.path.join(prefix, 'Library', 'bin'),
            os.path.join(prefix, 'Scripts'),
                ]
    else:
        paths = [
            os.path.join(prefix, 'bin'),
                ]
    # convert paths to shell-native paths
    return [shelldict['path_to'](path) for path in paths]


def pathlist_to_str(paths, escape_backslashes=True):
    """
    Format a path list, e.g., of bin paths to be added or removed,
    for user-friendly output.
    """
    path = ' and '.join(paths)
    if on_win and escape_backslashes:
        # escape for printing to console - ends up as single \
        path = re.sub(r'(?<!\\)\\(?!\\)', r'\\\\', path)
    else:
        path = path.replace("\\\\", "\\")
    return path


def get_activate_path(shelldict):
    arg_num = len(sys.argv)
    if arg_num != 4:
        num_expected = 2
        if arg_num < 4:
            raise TooFewArgumentsError(num_expected, arg_num - num_expected,
                                       "..activate expected exactly two arguments:\
                                        shell and env name")
        if arg_num > 4:
            raise TooManyArgumentsError(num_expected, arg_num - num_expected, sys.argv[2:],
                                        "..activate expected exactly two arguments:\
                                         shell and env name")
    binpath = binpath_from_arg(sys.argv[3], shelldict=shelldict)

    # prepend our new entries onto the existing path and make sure that the separator is native
    path = shelldict['pathsep'].join(binpath)
    return path


def main():
    from conda.base.constants import ROOT_ENV_NAME
    from conda.utils import shells

    # possible cases:
    #   > conda ..activate <SHELL> <ENV>
    #   > conda ..checkenv <SHELL> <ENV>
    #   > conda ..changeps1

    received = len(sys.argv)
    if received >= 2:
        mode = sys.argv[1].strip()
    if received >= 3:
        shell = sys.argv[2].strip()
    if received >= 4:
        env = sys.argv[3].strip()

    if '-h' in sys.argv or '--help' in sys.argv:
        # all unknown values will be listed after the -h/--help flag
        try:
            i = sys.argv.index("-h")
        except ValueError:
            i = sys.argv.index("--help")
        unknown = list(map(lambda s: s.strip(), sys.argv[i+1:]))

        help(mode, shell, unknown)
        # note: will never return from the help method

    if mode == '..activate':
        # conda ..activate <SHELL> <ENV>

        # don't count conda and ..activate
        received -= 2
        if received != 2:
            expected = 2
            offset = sys.argv[2:]
            opt_msg = "..activate expected exactly two arguments: SHELL and ENV"
            if received < 2:
                raise TooFewArgumentsError(expected, received, opt_msg)
            if received > 2:
                raise TooManyArgumentsError(expected, received, offset, opt_msg)

        binpath = binpath_from_arg(sys.argv[3], shelldict=shells[shell])

        # prepend our new entries onto the existing path and make sure that
        # the separator is native
        path = shells[shell]['path_delim'].join(binpath)

    # deactivation is handled completely in shell scripts - it restores backups
    # of env variables it is done in shell scripts because they handle state
    # much better than we can here

    elif mode == '..checkenv':
        # conda ..checkenv <SHELL> <ENV>

        # don't count conda and ..checkenv
        received -= 2
        if received != 2:
            expected = 2
            offset = sys.argv[2:]
            opt_msg = "..checkenv expected exactly two arguments: SHELL and ENV"
            if received < 2:
                raise TooFewArgumentsError(expected, received, opt_msg)
            if received > 2:
                raise TooManyArgumentsError(expected, received, offset, opt_msg)

        if env.lower() == ROOT_ENV_NAME.lower():
            # no need to check root env and try to install a symlink there
            sys.exit(0)
            # raise CondaSystemExit

        # this should throw an error and exit if the env or path can't be found.
        try:
            prefix = prefix_from_arg(env, shelldict=shells[shell])
        except ValueError as e:
            raise CondaValueError(text_type(e))

        # Make sure an env always has the conda symlink
        try:
            from conda.base.context import context
            import conda.install
            conda.install.symlink_conda(prefix, context.root_prefix, shell)
        except (IOError, OSError) as e:
            if e.errno == errno.EPERM or e.errno == errno.EACCES:
                raise CondaEnvironmentError(dedent("""\
                    Cannot activate environment {env}
                    User does not have write access for conda symlinks
                    """).format(env=env))
            raise
        sys.exit(0)
        # raise CondaSystemExit
    elif mode == '..changeps1':
        from conda.base.context import context
        path = int(context.changeps1)

    else:
        # This means there is a bug in main.py
        raise CondaValueError("unexpected command")

    # This print is actually what sets the PATH or PROMPT variable. The shell
    # script gets this value, and finishes the job.
    #
    # Must use sys.stdout.write(str(path)) to properly write to the console
    # cross platform, print(path) incorrectly prints integers on Windows
    sys.stdout.write(str(path))


if __name__ == '__main__':
    main()
