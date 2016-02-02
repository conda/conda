from __future__ import print_function, division, absolute_import

import errno
import os
from os.path import isdir, join, abspath
import re
import sys

from conda.cli.common import find_prefix_name


on_win = sys.platform == "win32"


def help():
    # sys.argv[1] will be ..checkenv in activate if an environment is already
    # activated
    if sys.argv[1] in ('..activate', '..checkenv'):
        if on_win:
            sys.exit("""Usage: activate ENV

adds the 'Scripts' and Library\bin directory of the environment ENV to the front of PATH.
ENV may either refer to just the name of the environment, or the full
prefix path.""")

        else:
            sys.exit("""Usage: source activate ENV

adds the 'bin' directory of the environment ENV to the front of PATH.
ENV may either refer to just the name of the environment, or the full
prefix path.""")
    else: # ..deactivate
        sys.exit("""Usage: source deactivate

removes the 'bin' directory of the environment activated with 'source
activate' from PATH. """)


def prefix_from_arg(arg):
    if os.sep in arg:
        if isdir(abspath(arg.strip("\""))):
            prefix = abspath(arg.strip("\""))
        else:
            sys.exit('Error: no such directory: %s' % arg)
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


def pathlist_to_str(paths):
    """
    Format a path list, e.g., of bin paths to be added or removed,
    for user-friendly output.
    """
    return ' and '.join([path.replace("\\\\", "\\") for path in paths])


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
            binpath = binpath_from_arg(sys.argv[2])
        else:
            sys.exit("Error: did not expect more than one argument")
        sys.stderr.write("prepending %s to PATH\n" % pathlist_to_str(binpath))
        path = os.pathsep.join([os.pathsep.join(binpath), path])

    elif sys.argv[1] == '..deactivate':
        if os.getenv("CONDA_DEFAULT_ENV"):
            binpath = binpath_from_arg(os.getenv('CONDA_DEFAULT_ENV'))
            if binpath:
                sys.stderr.write("discarding %s from PATH\n" % pathlist_to_str(binpath))
            path = path.replace(os.pathsep.join(binpath)+os.pathsep, "", 1)

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
            conda.install.symlink_conda(binpath[0], conda.config.root_dir)
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
