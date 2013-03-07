import os
import sys
from os.path import isdir, join



def help():
    if sys.argv[1] == '..activate':
        sys.exit("""Usage: source activate [ENV]

adds the 'bin' directory of the environment ENV to the front of PATH.
ENV may either refer to just the name of the environment, or the full
prefix path.  ENV defaults to: %s""" % sys.prefix)
    else: # ..deactivate
        sys.exit("""Usage: source deactivate [ENV]

removes the 'bin' directory of the environment ENV from PATH.
ENV may either refer to just the name of the environment, or the full
prefix path.  ENV defaults to: %s""" % sys.prefix)


def main():
    assert sys.argv[1] in ('..activate', '..deactivate')
    if '-h' in sys.argv or '--help' in sys.argv:
        help()

    if len(sys.argv) == 2:
        binpath = join(sys.prefix, 'bin')
    elif len(sys.argv) == 3:
        binpath = join(sys.prefix, 'envs', sys.argv[2], 'bin')
    else:
        sys.exit("Error: did not expect more than one argument")

    if sys.argv[1] == '..activate':
        if not isdir(binpath):
            sys.exit("Error: no such directory: %s" % binpath)
        paths = [binpath]
        sys.stderr.write("prepending %s to PATH\n" % binpath)
    else: # ..deactivate
        paths = []
        sys.stderr.write("discarding %s from PATH\n" % binpath)

    for path in os.getenv('PATH').split(os.pathsep):
        if path != binpath:
            paths.append(path)
    print os.pathsep.join(paths)


if __name__ == '__main__':
    main()
