import logging
from optparse import OptionParser

from conda.plan import execute_plan
from conda.api import get_index


def main():
    p = OptionParser(
        usage="usage: %prog [options] FILENAME",
        description="execute an conda plan")

    p.add_option('-q', '--quiet',
                 action="store_true")

    opts, args = p.parse_args()

    logging.basicConfig()

    if len(args) != 1:
        p.error('exactly one argument required')

    execute_plan(open(args[0]), get_index(), not opts.quiet)


if __name__ == '__main__':
    main()
