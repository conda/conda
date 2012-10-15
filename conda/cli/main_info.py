
from optparse import OptionParser


def main_info(args, conda, display_help=False):
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

    print
    print "Current Anaconda install:"
    print conda
    print

