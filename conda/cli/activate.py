from __future__ import print_function, division, absolute_import

import errno
import os
from os.path import isdir, join, abspath
import re
import sys

from conda.cli.common import find_prefix_name
from conda.utils import (translate_stream, unix_path_to_win, win_path_to_unix,
                         win_path_to_cygwin, find_parent_shell, shells, run_in)
import conda.config as config


on_win = sys.platform == "win32"


def help(command):
    # sys.argv[1] will be ..checkenv in activate if an environment is already
    # activated
    # get grandparent process name to see which shell we're using
    win_process = find_parent_shell()
    if command in ('..activate', '..checkenv'):
        if win_process in ["cmd.exe", "powershell.exe"]:
            sys.exit("""Usage: activate ENV

Adds the 'Scripts' and 'Library\\bin' directory of the environment ENV to the front of PATH.
ENV may either refer to just the name of the environment, or the full
prefix path.""")

        else:
            sys.exit("""Usage: source activate ENV

Adds the 'bin' directory of the environment ENV to the front of PATH.
ENV may either refer to just the name of the environment, or the full
prefix path.""")
    elif command == '..deactivate':
        if win_process in ["cmd.exe", "powershell.exe"]:
            sys.exit("""Usage: deactivate

Removes the environment prefix, 'Scripts' and 'Library\\bin' directory
of the environment ENV from the front of PATH.""")
        else:
            sys.exit("""Usage: source deactivate

Removes the 'bin' directory of the environment activated with 'source
activate' from PATH. """)
    else:
        sys.exit("No help available for command %s" % sys.argv[1])


def prefix_from_arg(arg, shelldict):
    if shelldict['sep'] in arg:
        # strip is removing " marks, not \ - look carefully
        native_path = shelldict['path_from'](arg)
        if isdir(abspath(native_path.strip("\""))):
            prefix = abspath(native_path.strip("\""))
        else:
            raise ValueError('could not find environment: %s' % native_path)
    else:
        prefix = find_prefix_name(arg)
        if prefix is None:
            raise ValueError('could not find environment: %s' % arg)
    return shelldict['path_to'](prefix)


def binpath_from_arg(arg, shelldict):
    # prefix comes back as platform-native path
    prefix = prefix_from_arg(arg, shelldict=shelldict)
    if sys.platform == 'win32':
        paths = [prefix.rstrip("\\"),
                 os.path.join(prefix, 'Library', 'bin'),
                 os.path.join(prefix, 'Scripts'),
               ]
    else:
        paths = [os.path.join(prefix, 'bin'),
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


def get_path(shelldict):
    """Get path using a subprocess call.

    os.getenv path isn't good for us, since bash on windows has a wildly different path from Windows.

    This returns PATH in the native representation of the shell - not necessarily the native representation
    of the platform
    """
    return run_in(shelldict["printpath"], shelldict)[0]


def main():
    from conda.config import root_env_name, root_dir, changeps1
    import conda.install
    if '-h' in sys.argv or '--help' in sys.argv:
        help(sys.argv[1])

    path = None
    shell = find_parent_shell(path=False)
    shelldict = shells[shell]
    if sys.argv[1] == '..activate':
        path = get_path(shelldict)
        if len(sys.argv) == 2 or sys.argv[2].lower() == root_env_name.lower():
            binpath = binpath_from_arg(root_env_name, shelldict=shelldict)
            rootpath = None
        elif len(sys.argv) == 3:
            binpath = binpath_from_arg(sys.argv[2], shelldict=shelldict)
            rootpath = binpath_from_arg(root_env_name, shelldict=shelldict)
        else:
            sys.exit("Error: did not expect more than one argument")
        sys.stderr.write("prepending %s to PATH\n" % shelldict['path_to'](pathlist_to_str(binpath)))

        # Clear the root path if it is present
        if rootpath:
            path = path.replace(shelldict['pathsep'].join(rootpath), "")

        # prepend our new entries onto the existing path and make sure that the separator is native
        path = shelldict['pathsep'].join(binpath + [path,])

    # deactivation is handled completely in shell scripts - it restores backups of env variables.
    #    It is done in shell scripts because they handle state much better than we can here.

    elif sys.argv[1] == '..checkenv':
        if len(sys.argv) < 3:
            sys.argv.append(root_env_name)
        if len(sys.argv) > 3:
            sys.exit("Error: did not expect more than one argument.")
        if sys.argv[2].lower() == root_env_name.lower():
            # no need to check root env and try to install a symlink there
            sys.exit(0)

        # this should throw an error and exit if the env or path can't be found.
        try:
            binpath = binpath_from_arg(sys.argv[2], shelldict=shelldict)
        except ValueError as e:
            sys.exit(e.message)

        # Make sure an env always has the conda symlink
        try:
            conda.install.symlink_conda(shelldict['path_from'](binpath[0]), root_dir, shell)
        except (IOError, OSError) as e:
            if e.errno == errno.EPERM or e.errno == errno.EACCES:
                msg = ("Cannot activate environment {0}, not have write access to conda symlink"
                       .format(sys.argv[2]))
                sys.exit(msg)
            raise
        sys.exit(0)

    elif sys.argv[1] == '..setps1':
        # path is a bit of a misnomer here.  It is the prompt setting.  However, it is returned
        #    below by printing.  That is why it is named "path"
        # DO NOT use os.getenv for this.  One Windows especially, it shows cmd.exe settings
        #    for bash shells.  This method uses the shell directly.
        path, _ = run_in(shelldict['printps1'], shelldict, env=os.environ.copy())
        # failsafes
        if not path:
            if shelldict['exe'] == 'cmd.exe':
                path = '$P$G'
        # strip off previous prefix, if any:
        path = re.sub(".*\(\(.*\)\)\ ", "", path, count=1)
        env_path = sys.argv[2]
        if changeps1 and env_path:
            path = "(({})) {}".format(os.path.split(env_path)[-1], path)

    else:
        # This means there is a bug in main.py
        raise ValueError("unexpected command")

    # This print is actually what sets the PATH or PROMPT variable.  The shell
    # script gets this value, and finishes the job.
    print(path)


if __name__ == '__main__':
    main()
