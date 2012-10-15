

from optparse import OptionParser


def main_locations(args, conda, display_help=False):
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

    print "System location for Anaconda environments:"
    print
    print '    %s' % conda.system_location

    if conda.user_locations:
        print
        print "User locations for Anaconda environments:"
        print
        for location in conda.user_locations:
            print "    %s" % location
        print



