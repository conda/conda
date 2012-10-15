
from optparse import OptionParser


def main_envs(args, conda, display_help=False):
    p = OptionParser(
        usage       = "usage: conda envs",
        description = "List all known Anaconda environments."
    )

    if display_help:
        p.print_help()
        return

    opts, args = p.parse_args(args)

    if len(args) > 0:
        p.error('too many arguments')

    envs = conda.environments

    print "Known Anaconda environments:"
    print

    for env in envs:
        print "    %s" % env.prefix
    print

