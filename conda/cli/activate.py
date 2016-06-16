from __future__ import print_function, division, absolute_import

import errno
import os
from os.path import isdir, abspath
import re
import sys

from conda.cli.common import find_prefix_name
from conda.utils import (shells, run_in)


on_win = sys.platform == "win32"


def help(command, shell):
    # sys.argv[1] will be ..checkenv in activate if an environment is already
    # activated
    # get grandparent process name to see which shell we're using
    if command in ('..activate', '..checkenv'):
        if shell in ["cmd.exe", "powershell.exe"]:
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
        if shell in ["cmd.exe", "powershell.exe"]:
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
    'Returns a platform-native path'
    # MSYS2 converts Unix paths to Windows paths with unix seps
    # so we must check for the drive identifier too.
    if shelldict['sep'] in arg and not re.match('[a-zA-Z]:', arg):
        # strip is removing " marks, not \ - look carefully
        native_path = shelldict['path_from'](arg)
        if isdir(abspath(native_path.strip("\""))):
            prefix = abspath(native_path.strip("\""))
        else:
            raise ValueError('could not find environment: %s' % native_path)
    else:
        prefix = find_prefix_name(arg.replace('/', os.path.sep))
        if prefix is None:
            raise ValueError('could not find environment: %s' % arg)
    return prefix


def binpath_from_arg(arg, shelldict):
    # prefix comes back as platform-native path
    prefix = prefix_from_arg(arg, shelldict=shelldict)
    if sys.platform == 'win32':
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


def get_path(shelldict):
    """Get path using a subprocess call.

    os.getenv path isn't good for us, since bash on windows has a wildly different
    path from Windows.

    This returns PATH in the native representation of the shell - not necessarily
    the native representation of the platform
    """
    return run_in(shelldict["printpath"], shelldict)[0]


def main():
    from conda.config import root_env_name, root_dir, changeps1
    import conda.install
    if '-h' in sys.argv or '--help' in sys.argv:
        # all execution paths sys.exit at end.
        help(sys.argv[1], sys.argv[2])

    shell = sys.argv[2]
    shelldict = shells[shell]
    if sys.argv[1] == '..activate':
        path = get_path(shelldict)
        if len(sys.argv) == 3 or sys.argv[3].lower() == root_env_name.lower():
            binpath = binpath_from_arg(root_env_name, shelldict=shelldict)
            rootpath = None
        elif len(sys.argv) == 4:
            binpath = binpath_from_arg(sys.argv[3], shelldict=shelldict)
            rootpath = binpath_from_arg(root_env_name, shelldict=shelldict)
        else:
            sys.exit("Error: did not expect more than one argument")
        pathlist_str = pathlist_to_str(binpath)
        sys.stderr.write("prepending %s to PATH\n" % shelldict['path_to'](pathlist_str))

        # Clear the root path if it is present
        if rootpath:
            path = path.replace(shelldict['pathsep'].join(rootpath), "")

        path = path.lstrip()
        # prepend our new entries onto the existing path and make sure that the separator is native
        path = shelldict['pathsep'].join(binpath + [path, ])
        # Clean up any doubled-up path separators
        path = path.replace(shelldict['pathsep'] * 2, shelldict['pathsep'])

    # deactivation is handled completely in shell scripts - it restores backups of env variables.
    #    It is done in shell scripts because they handle state much better than we can here.

    elif sys.argv[1] == '..checkenv':
        if len(sys.argv) < 4:
            sys.argv.append(root_env_name)
        if len(sys.argv) > 4:
            sys.exit("Error: did not expect more than one argument.")
        if sys.argv[3].lower() == root_env_name.lower():
            # no need to check root env and try to install a symlink there
            sys.exit(0)

        # this should throw an error and exit if the env or path can't be found.
        try:
            prefix = prefix_from_arg(sys.argv[3], shelldict=shelldict)
        except ValueError as e:
            sys.exit(getattr(e, 'message', e))

        # Make sure an env always has the conda symlink
        try:
            conda.install.symlink_conda(prefix, root_dir, shell)
        except (IOError, OSError) as e:
            if e.errno == errno.EPERM or e.errno == errno.EACCES:
                msg = ("Cannot activate environment {0}.\n"
                       "User does not have write access for conda symlinks."
                       .format(sys.argv[2]))
                sys.exit(msg)
            raise
        sys.exit(0)

    elif sys.argv[1] == '..setps1':
        # path is a bit of a misnomer here.  It is the prompt setting.  However, it is returned
        #    below by printing.  That is why it is named "path"
        # DO NOT use os.getenv for this.  One Windows especially, it shows cmd.exe settings
        #    for bash shells.  This method uses the shell directly.
        path = os.getenv(shelldict['promptvar'], '')
        # failsafes
        if not path:
            if shelldict['exe'] == 'cmd.exe':
                path = '$P$G'
        # strip off previous prefix, if any:
        path = re.sub(".*\(\(.*\)\)\ ", "", path, count=1)
        env_path = sys.argv[3]
        if changeps1 and env_path:
            path = "(({0})) {1}".format(os.path.split(env_path)[-1], path)

    else:
        # This means there is a bug in main.py
        raise ValueError("unexpected command")

    # This print is actually what sets the PATH or PROMPT variable.  The shell
    # script gets this value, and finishes the job.
    print(path)


if __name__ == '__main__':
    main()
