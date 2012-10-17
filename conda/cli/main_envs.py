
from optparse import OptionParser

from config import config

def main_envs(args, display_help=False):
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

    conf = config()

    envs = conf.environments

    print "Known Anaconda environments:"
    print

    for env in envs:
        print "    %s" % env.prefix
    print

