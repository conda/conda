from __future__ import print_function, division, absolute_import

import os
import sys
from os.path import isdir, join, abspath

from conda.cli.common import find_prefix_name

def help():
    # sys.argv[1] will be ..checkenv in activate if an environment is already
    # activated
    if sys.argv[1] in ('..activate', '..checkenv'):
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
        return abspath(arg)
    prefix = find_prefix_name(arg)
    if prefix is None:
        sys.exit('Error: could not find environment: %s' % arg)
    return prefix


def binpath_from_arg(arg):
    path = join(prefix_from_arg(arg), 'bin')
    if not isdir(path):
        sys.exit("Error: no such directory: %s" % path)
    return path

def main():
    if '-h' in sys.argv or '--help' in sys.argv:
        help()

    if sys.argv[1] == '..activate':
        if len(sys.argv) == 2:
            sys.exit("Error: no environment provided.")
        elif len(sys.argv) == 3:
            binpath = binpath_from_arg(sys.argv[2])
        else:
            sys.exit("Error: did not expect more than one argument")

        paths = [binpath]
        sys.stdout.write("prepending %s to PATH\n" % binpath)

    elif sys.argv[1] == '..deactivate':
        if len(sys.argv) != 2:
            sys.exit("Error: too many arguments.")

        try:
            binpath = binpath_from_arg(os.getenv('CONDA_DEFAULT_ENV', 'root'))
        except SystemExit:
            print(os.environ['PATH'])
            raise
        paths = []
        sys.stdout.write("discarding %s from PATH\n" % binpath)

    elif sys.argv[1] == '..activateroot':
        if len(sys.argv) != 2:
            sys.exit("Error: too many arguments.")

        if 'CONDA_DEFAULT_ENV' not in os.environ:
            sys.exit("Error: No environment to deactivate")
        try:
            import conda.config
            binpath = binpath_from_arg(os.getenv('CONDA_DEFAULT_ENV'))
            rootpath = binpath_from_arg(conda.config.root_env_name)
        except SystemExit:
            print(os.environ['PATH'])
            raise
        # deactivate is the same as activate root (except without setting
        # CONDA_DEFAULT_ENV or PS1). XXX: The user might want to put the root
        # env back somewhere in the middle of the PATH, not at the beginning.
        if rootpath not in os.getenv('PATH').split(os.pathsep):
            paths = [rootpath]
        else:
            paths = []
        sys.stdout.write("discarding %s from PATH\n" % binpath)

    elif sys.argv[1] == '..checkenv':
        if len(sys.argv) < 3:
            sys.exit("Error: no environment provided.")
        if len(sys.argv) > 3:
            sys.exit("Error: did not expect more than one argument.")
        binpath = binpath_from_arg(sys.argv[2])
        # Make sure an env always has the conda symlink
        try:
            import conda.config
            if binpath != join(conda.config.root_dir, 'bin'):
                import conda.install
                conda.install.symlink_conda(join(binpath, '..'), conda.config.root_dir)
        except (IOError, OSError) as e:
            import errno
            if e.errno == errno.EPERM or e.errno == errno.EACCES:
                sys.exit("Cannot activate environment {}, do not have write access to write conda symlink".format(sys.argv[2]))
            raise
        sys.exit(0)

    else:
        # This means there is a bug in main.py
        raise ValueError("unexpected command")

    for path in os.getenv('PATH').split(os.pathsep):
        if path != binpath:
            paths.append(path)
    print(os.pathsep.join(paths))


if __name__ == '__main__':
    main()
