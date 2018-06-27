# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

import os
from os.path import abspath, isdir
import re as regex
import sys

from ..common.compat import ensure_text_type, on_win, text_type
from ..utils import shells


def help(command, shell):
    # sys.argv[1] will be ..checkenv in activate if an environment is already
    # activated
    # get grandparent process name to see which shell we're using
    if command in ('..activate', '..checkenv'):
        if shell in ["cmd.exe", "powershell.exe"]:
            from ..exceptions import CondaSystemExit
            raise CondaSystemExit("""Usage: activate ENV

Adds the 'Scripts' and 'Library\\bin' directory of the environment ENV to the front of PATH.
ENV may either refer to just the name of the environment, or the full
prefix path.""")

        else:
            from ..exceptions import CondaSystemExit
            raise CondaSystemExit("""Usage: source activate ENV

Adds the 'bin' directory of the environment ENV to the front of PATH.
ENV may either refer to just the name of the environment, or the full
prefix path.""")
    elif command == '..deactivate':
        if shell in ["cmd.exe", "powershell.exe"]:
            from ..exceptions import CondaSystemExit
            raise CondaSystemExit("""Usage: deactivate

Removes the environment prefix, 'Scripts' and 'Library\\bin' directory
of the environment ENV from the front of PATH.""")
        else:
            from ..exceptions import CondaSystemExit
            raise CondaSystemExit("""Usage: source deactivate

Removes the 'bin' directory of the environment activated with 'source
activate' from PATH. """)
    else:
        from ..exceptions import CondaSystemExit
        raise CondaSystemExit("No help available for command %s" % ensure_text_type(sys.argv[1]))


def locate_prefix_by_name(ctx, name):
    from ..base.context import locate_prefix_by_name
    return locate_prefix_by_name(name, ctx.envs_dirs)


def prefix_from_arg(arg, shell):
    shelldict = shells[shell] if shell else {}
    from ..base.context import context
    'Returns a platform-native path'
    # MSYS2 converts Unix paths to Windows paths with unix seps
    # so we must check for the drive identifier too.
    if shelldict['sep'] in arg and not regex.match('[a-zA-Z]:', arg):
        # strip is removing " marks, not \ - look carefully
        native_path = shelldict['path_from'](arg)
        if isdir(abspath(native_path.strip("\""))):
            prefix = abspath(native_path.strip("\""))
        else:
            from ..exceptions import CondaValueError
            raise CondaValueError('Could not find environment: %s' % native_path)
    else:
        prefix = locate_prefix_by_name(context, arg.replace('/', os.path.sep))
    return prefix


def _get_prefix_paths(prefix):
    if on_win:
        yield prefix.rstrip("\\")
        yield os.path.join(prefix, 'Library', 'mingw-w64', 'bin')
        yield os.path.join(prefix, 'Library', 'usr', 'bin')
        yield os.path.join(prefix, 'Library', 'bin')
        yield os.path.join(prefix, 'Scripts')
        yield os.path.join(prefix, 'bin')
    else:
        yield os.path.join(prefix, 'bin')


def binpath_from_arg(arg, shell, going_to_shell=True):
    shelldict = shells[shell] if shell else {}
    # prefix comes back as platform-native path
    prefix = prefix_from_arg(arg, shell)
    # convert paths to shell-native paths
    if going_to_shell:
        return [shelldict['path_to'](path) for path in _get_prefix_paths(prefix)]
    else:
        return [path for path in _get_prefix_paths(prefix)]


def pathlist_to_str(paths, escape_backslashes=True):
    """
    Format a path list, e.g., of bin paths to be added or removed,
    for user-friendly output.
    """
    path = ' and '.join(paths)
    if on_win and escape_backslashes:
        # escape for printing to console - ends up as single \
        path = regex.sub(r'(?<!\\)\\(?!\\)', r'\\\\', path)
    else:
        path = path.replace("\\\\", "\\")
    return path


def get_activate_path(prefix, shell, going_to_shell=True):
    shelldict = shells[shell] if shell else {}
    binpath = binpath_from_arg(prefix, shell, going_to_shell)

    # prepend our new entries onto the existing path and make sure that the separator is native
    if going_to_shell:
        path = shelldict['pathsep'].join(binpath)
    else:
        path = os.pathsep.join(binpath)
    return path


def main():
    print("WARNING: The module conda.cli.activate is deprecated. It will be removed in a "
          "future feature release (i.e. minor version release).", file=sys.stderr)

    from ..base.constants import ROOT_ENV_NAME
    from ..gateways.logging import initialize_logging
    initialize_logging()

    sys_argv = tuple(ensure_text_type(s) for s in sys.argv)

    if '-h' in sys_argv or '--help' in sys_argv:
        # all execution paths sys.exit at end.
        help(sys_argv[1], sys_argv[2])

    if len(sys_argv) > 2:
        shell = sys_argv[2]
    else:
        shell = ''

    if regex.match('^..(?:de|)activate$', sys_argv[1]):
        arg_num = len(sys_argv)
        if arg_num != 4:
            num_expected = 2
            if arg_num < 4:
                from ..exceptions import TooFewArgumentsError
                raise TooFewArgumentsError(num_expected, arg_num - num_expected,
                                           "{} expected exactly two arguments:\
                                            shell and env name".format(sys_argv[1]))
            if arg_num > 4:
                from ..exceptions import TooManyArgumentsError
                raise TooManyArgumentsError(num_expected, arg_num - num_expected, sys_argv[2:],
                                            "{} expected exactly two arguments:\
                                             shell and env name".format(sys_argv[1]))

    if sys_argv[1] == '..activate':
        print(get_activate_path(sys_argv[3], shell, True))
        sys.exit(0)

    elif sys_argv[1] == '..deactivate.path':
        activation_path = get_activate_path(sys_argv[3], shell, False)

        if os.getenv('_CONDA_HOLD'):
            new_path = regex.sub(r'%s(:?)' % regex.escape(activation_path),
                                 r'CONDA_PATH_PLACEHOLDER\1',
                                 os.environ[str('PATH')], 1)
        else:
            new_path = regex.sub(r'%s(:?)' % regex.escape(activation_path), r'',
                                 os.environ[str('PATH')], 1)

        new_path = shells[shell]['path_to'](new_path)
        print(new_path)
        sys.exit(0)

    elif sys_argv[1] == '..checkenv':
        if len(sys_argv) < 4:
            from ..exceptions import ArgumentError
            raise ArgumentError("Invalid arguments to checkenv.  Need shell and env name/path")
        if len(sys_argv) > 4:
            from ..exceptions import ArgumentError
            raise ArgumentError("did not expect more than one argument.")
        if sys_argv[3].lower() == ROOT_ENV_NAME.lower():
            # no need to check root env and try to install a symlink there
            sys.exit(0)
            # raise CondaSystemExit

        # this should throw an error and exit if the env or path can't be found.
        try:
            prefix_from_arg(sys_argv[3], shell)
        except ValueError as e:
            from ..exceptions import CondaValueError
            raise CondaValueError(text_type(e))

        # # Make sure an env always has the conda symlink
        # try:
        #     from conda.base.context import context
        #     import conda.install
        #     conda.install.symlink_conda(prefix, context.root_prefix, shell)
        # except (IOError, OSError) as e:
        #     if e.errno == errno.EPERM or e.errno == errno.EACCES:
        #         msg = ("Cannot activate environment {0}.\n"
        #                "User does not have write access for conda symlinks."
        #                .format(sys.argv[2]))
        #         raise CondaEnvironmentError(msg)
        #     raise

        sys.exit(0)
        # raise CondaSystemExit
    elif sys_argv[1] == '..changeps1':
        from ..base.context import context
        path = int(context.changeps1)

    else:
        # This means there is a bug in main.py
        from ..exceptions import CondaValueError
        raise CondaValueError("unexpected command")

    # This print is actually what sets the PATH or PROMPT variable.  The shell
    # script gets this value, and finishes the job.
    print(path)


print("WARNING: The conda.cli.activate module is deprecated and will be removed in a "
      "future release.", file=sys.stderr)


if __name__ == '__main__':
    main()
