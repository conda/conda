from __future__ import print_function, division, absolute_import

import os
import sys
from os.path import isdir, join

import conda.config

def help():
    if sys.argv[1] == '..activate':
        sys.exit("""Usage: source activate ENV

adds the 'bin' directory of the environment ENV to the front of PATH.
ENV may either refer to just the name of the environment, or the full
prefix path.""")
    else: # ..deactivate
        sys.exit("""Usage: source deactivate

removes the 'bin' directory of the environment activated with 'source
activate' from PATH. """)


def main():
    if '-h' in sys.argv or '--help' in sys.argv:
        help()

    if sys.argv[1] == '..activate':
        if len(sys.argv) == 2:
            sys.exit("Error: no environment provided.")
        elif len(sys.argv) == 3:
            binpath = join(conda.config.root_dir, 'envs', sys.argv[2], 'bin')
        else:
            sys.exit("Error: did not expect more than one argument")

        if not isdir(binpath):
            sys.exit("Error: no such directory: %s" % binpath)
        paths = [binpath]
        sys.stderr.write("prepending %s to PATH\n" % binpath)

    elif sys.argv[1] == '..deactivate':
        if len(sys.argv) != 2:
            sys.exit("Error: too many arguments.")

        if 'CONDA_DEFAULT_ENV' not in os.environ:
            sys.exit("Error: No environment to deactivate")
        binpath = join(conda.config.root_dir, 'envs',
            os.getenv('CONDA_DEFAULT_ENV'), 'bin')
        paths = []
        sys.stderr.write("discarding %s from PATH\n" % binpath)

    elif sys.argv[1] == '..checkenv':
        binpath = join(conda.config.root_dir, 'envs', sys.argv[2], 'bin')
        if not isdir(binpath):
            sys.exit("Error: no such directory: %s" % binpath)
        sys.exit(0)

    else:
        # This means there is a big in main.py
        raise ValueError("unexpected command")

    for path in os.getenv('PATH').split(os.pathsep):
        if path != binpath:
            paths.append(path)
    print(os.pathsep.join(paths))


if __name__ == '__main__':
    main()
