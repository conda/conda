# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from conda.config import Config


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'info',
        description     = "Display information about current Anaconda install.",
        help            = "Display information about current Anaconda install.",
    )
    elgroup = p.add_mutually_exclusive_group()
    elgroup.add_argument(
        '-e', "--envs",
        action  = "store_true",
        default = False,
        help    = "list all known Anaconda environments.",
    )
    elgroup.add_argument(
        '-l', "--locations",
        action  = "store_true",
        default = False,
        help    = "list known locations for Anaconda environments.",
    )
    p.set_defaults(func=execute)


def execute(args):

    conf = Config()

    if args.envs:
        env_paths = conf.environment_paths

        print "Known Anaconda environments:"
        print

        for path in env_paths:
            print "    %s" % path
        print

    elif args.locations:
        print
        print "Locations for Anaconda environments:"
        print
        for location in conf.locations:
            print "    %s" % location,
            if location == conf.system_location:
                print " (system location)",
            print
        print

    else:
        print
        print "Current Anaconda install:"
        print conf
        print

