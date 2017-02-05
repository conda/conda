from __future__ import print_function, division, absolute_import, unicode_literals

import errno
import os
import re
import sys
from os.path import isdir, abspath

from ..common.compat import text_type, on_win
from ..exceptions import (CondaSystemExit, ArgumentError, CondaValueError, CondaEnvironmentError,
                          TooManyArgumentsError, TooFewArgumentsError)


def help(command, shell):
    # sys.argv[1] will be ..checkenv in activate if an environment is already
    # activated
    # get grandparent process name to see which shell we're using
    if command in ('..activate', '..checkenv'):
        if shell in ["cmd.exe", "powershell.exe"]:
            raise CondaSystemExit("""Usage: activate ENV

Adds the 'Scripts' and 'Library\\bin' directory of the environment ENV to the front of PATH.
ENV may either refer to just the name of the environment, or the full
prefix path.""")

        else:
            raise CondaSystemExit("""Usage: source activate ENV

Adds the 'bin' directory of the environment ENV to the front of PATH.
ENV may either refer to just the name of the environment, or the full
prefix path.""")
    elif command == '..deactivate':
        if shell in ["cmd.exe", "powershell.exe"]:
            raise CondaSystemExit("""Usage: deactivate

Removes the environment prefix, 'Scripts' and 'Library\\bin' directory
of the environment ENV from the front of PATH.""")
        else:
            raise CondaSystemExit("""Usage: source deactivate

Removes the 'bin' directory of the environment activated with 'source
activate' from PATH. """)
    else:
        raise CondaSystemExit("No help available for command %s" % sys.argv[1])


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
            raise CondaValueError('Could not find environment: %s' % native_path)
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
    if '-h' in sys.argv or '--help' in sys.argv:
        # all execution paths sys.exit at end.
        help(sys.argv[1], sys.argv[2])

    if len(sys.argv) > 2:
        shell = sys.argv[2]
        shelldict = shells[shell]
    else:
        shelldict = {}

    if sys.argv[1] == '..activate':
        print(get_activate_path(shelldict))
        sys.exit(0)

    elif sys.argv[1] == '..deactivate.path':
        import re
        activation_path = get_activate_path(shelldict)

        if os.getenv('_CONDA_HOLD'):
            new_path = re.sub(r'%s(:?)' % re.escape(activation_path),
                              r'CONDA_PATH_PLACEHOLDER\1',
                              os.environ[str('PATH')], 1)
        else:
            new_path = re.sub(r'%s(:?)' % re.escape(activation_path), r'',
                              os.environ[str('PATH')], 1)

        print(new_path)
        sys.exit(0)

    elif sys.argv[1] == '..checkenv':
        if len(sys.argv) < 4:
            raise ArgumentError("Invalid arguments to checkenv.  Need shell and env name/path")
        if len(sys.argv) > 4:
            raise ArgumentError("did not expect more than one argument.")
        if sys.argv[3].lower() == ROOT_ENV_NAME.lower():
            # no need to check root env and try to install a symlink there
            sys.exit(0)
            # raise CondaSystemExit

        # this should throw an error and exit if the env or path can't be found.
        try:
            prefix = prefix_from_arg(sys.argv[3], shelldict=shelldict)
        except ValueError as e:
            raise CondaValueError(text_type(e))

        # Make sure an env always has the conda symlink
        try:
            from conda.base.context import context
            import conda.install
            conda.install.symlink_conda(prefix, context.root_prefix, shell)
        except (IOError, OSError) as e:
            if e.errno == errno.EPERM or e.errno == errno.EACCES:
                msg = ("Cannot activate environment {0}.\n"
                       "User does not have write access for conda symlinks."
                       .format(sys.argv[2]))
                raise CondaEnvironmentError(msg)
            raise
        sys.exit(0)
        # raise CondaSystemExit
    elif sys.argv[1] == '..changeps1':
        from conda.base.context import context
        path = int(context.changeps1)

    else:
        # This means there is a bug in main.py
        raise CondaValueError("unexpected command")

    # This print is actually what sets the PATH or PROMPT variable.  The shell
    # script gets this value, and finishes the job.
    print(path)


if __name__ == '__main__':
    main()
