from __future__ import print_function, division, absolute_import

import errno
import os
from os.path import isdir, join, abspath
import psutil
import re
import sys

from conda.cli.common import find_prefix_name
from conda.utils import translate_stream, unix_path_to_win, win_path_to_unix, win_path_to_cygwin


on_win = sys.platform == "win32"

def find_parent_shell(path=False):
    """return process name or path of parent.  Default is to return only name of process."""
    process = psutil.Process()
    while "conda" in process.parent().name():
        process = process.parent()
    if path:
        return process.parent().exe()
    return process.parent().name()


on_win = sys.platform == "win32"


def help():
    # sys.argv[1] will be ..checkenv in activate if an environment is already
    # activated
    # get grandparent process name to see which shell we're using
    win_process = find_parent_shell()
    if sys.argv[1] in ('..activate', '..checkenv'):
        if on_win and win_process in ["cmd.exe", "powershell.exe"]:
            sys.exit("""Usage: activate ENV

adds the 'Scripts' and 'Library\bin' directory of the environment ENV to the front of PATH.
ENV may either refer to just the name of the environment, or the full
prefix path.""")

        else:
            sys.exit("""Usage: source activate ENV

adds the 'bin' directory of the environment ENV to the front of PATH.
ENV may either refer to just the name of the environment, or the full
prefix path.""")
    else: # ..deactivate
        if on_win and win_process in ["cmd.exe", "powershell.exe"]:
            sys.exit("""Usage: deactivate

Removes the 'Scripts' and 'Library\bin' directory of the environment ENV to the front of PATH.""")
        else:
            sys.exit("""Usage: source deactivate

removes the 'bin' directory of the environment activated with 'source
activate' from PATH. """)


def prefix_from_arg(arg):
    if os.sep in arg:
        if isdir(abspath(arg.strip("\""))):
            prefix = abspath(arg.strip("\""))
        else:
            sys.exit('Error: could not find environment: %s' % arg)
    else:
        prefix = find_prefix_name(arg)
        if prefix is None:
            sys.exit('Error: could not find environment: %s' % arg)
    return prefix


def binpath_from_arg(arg):
    prefix = prefix_from_arg(arg)
    if on_win:
        path = [prefix.rstrip("\\"),
                join(prefix, 'cmd'),
                join(prefix, 'Scripts'),
                join(prefix, 'Library', 'bin'),
               ]
    else:
        path = [prefix.rstrip("/"),
                join(prefix, 'cmd'),
                join(prefix, 'bin'),
                ]
    return path


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


def main():
    import conda.config
    import conda.install
    if '-h' in sys.argv or '--help' in sys.argv:
        help()

    path = os.getenv("PATH")
    # This one is because we force Library/bin to be on PATH on windows.  Strip it off here.
    if on_win:
        path = path.replace(join(sys.prefix, "Library", "bin")+os.pathsep, "", 1)

    if sys.argv[1] == '..activate':
        if len(sys.argv) == 2:
            binpath = binpath_from_arg("root")
        elif len(sys.argv) == 3:
            base_path = sys.argv[2]
            parent_shell = find_parent_shell(path=True)
            if any([shell in parent_shell for shell in ["cmd.exe", "powershell.exe"]]):
                base_path = translate_stream(base_path, unix_path_to_win)
            elif 'cygwin' in parent_shell:
                # this should be harmless to unix paths, but converts win paths to unix for bash on win (msys, cygwin)
                base_path = translate_stream(base_path, win_path_to_cygwin)
            else:
                base_path = translate_stream(base_path, win_path_to_unix)
            binpath = binpath_from_arg(base_path)
        else:
            sys.exit("Error: did not expect more than one argument")
        sys.stderr.write("prepending %s to PATH\n" % pathlist_to_str(binpath))
        path = os.pathsep.join([os.pathsep.join(binpath), path])

    elif sys.argv[1] == '..deactivate':
        path = os.getenv("CONDA_PATH_BACKUP", None)
        sys.stderr.write("path:")
        sys.stderr.write(path)
        if path:
            sys.stderr.write("Restoring PATH to deactivated state\n")
        else:
            path = os.getenv("PATH")  # effectively a no-op; just set PATH to what it already is

    elif sys.argv[1] == '..checkenv':
        if len(sys.argv) < 3:
            sys.exit("Error: no environment provided.")
        if len(sys.argv) > 3:
            sys.exit("Error: did not expect more than one argument.")
        if sys.argv[2] == 'root':
            # no need to check root env and try to install a symlink there
            sys.exit(0)
        binpath = binpath_from_arg(sys.argv[2])  # this should throw an error and exit if the env or path can't be found.
        # Make sure an env always has the conda symlink
        try:
            conda.install.symlink_conda(binpath[0], conda.config.root_dir, find_parent_shell())
        except (IOError, OSError) as e:
            if e.errno == errno.EPERM or e.errno == errno.EACCES:
                sys.exit("Cannot activate environment {}, do not have write access to write conda symlink".format(sys.argv[2]))
            raise
        sys.exit(0)

    elif sys.argv[1] == '..setps1':
        # path is a bit of a misnomer here.  It is the prompt setting.  However, it is returned
        #    below by printing.  That is why it is named "path"
        path = sys.argv[3]
        if not path:
            if on_win:
                path = os.getenv("PROMPT", "$P$G")
            else:
                # zsh uses prompt.  If it exists, prefer it.
                path = os.getenv("PROMPT")
                # fall back to bash default
                if not path:
                    path = os.getenv("PS1")
        # strip off previous prefix, if any:
        path = re.sub(".*\(\(.*\)\)\ ", "", path, count=1)
        env_path = sys.argv[2]
        if conda.config.changeps1 and env_path:
            path = "(({})) {}".format(os.path.split(env_path)[-1], path)

    else:
        # This means there is a bug in main.py
        raise ValueError("unexpected command")

    # This print is actually what sets the PATH or PROMPT variable.  The shell script gets this value, and finishes the job.
    print(path)


if __name__ == '__main__':
    main()
