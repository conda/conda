
from optparse import OptionParser

from config import config

def main_info(args, display_help=False):
    p = OptionParser(
        usage       = "usage: conda info",
        description = "Display information about current Anaconda install."
    )

    if display_help:
        p.print_help()
        return

    opts, args = p.parse_args(args)

    if len(args) > 0:
        p.error('too many arguments')

    conf = config()

    print
    print "Current Anaconda install:"
    print conf
    print

