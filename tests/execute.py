import logging
from optparse import OptionParser

from conda.instructions import execute_instructions
from conda.api import get_index
import yaml

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

    plan = yaml.load(open(args[0]))
    print plan
    execute_instructions(plan, get_index(), not opts.quiet)


if __name__ == '__main__':
    main()
