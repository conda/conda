

from optparse import OptionParser

from config import config


def main_locations(args, display_help=False):
    p = OptionParser(
        usage       = "usage: conda locations [options]",
        description = "List or modify known locations for Anaconda environments.",
    )
    # p.add_option(
    #     '-a', "--add",
    #     action  = "store",
    #     default = None,
    #     help    = "path to add as an Anaconda location",
    # )
    # p.add_option(
    #     '-r', "--remove",
    #     action  = "store",
    #     default = None,
    #     help    = "path to remove as an Anaconda location",
    # )

    if display_help:
        p.print_help()
        return

    opts, args = p.parse_args(args)

    if len(args) > 0:
        p.error('too many arguments')

    # if opts.add and opts.remove:
    #     p.error('--add and --remove are mutually exclusive')

    conf = config()

    print "System location for Anaconda environments:"
    print
    print '    %s' % conf.system_location

    if conf.user_locations:
        print
        print "User locations for Anaconda environments:"
        print
        for location in conf.user_locations:
            print "    %s" % location
        print



