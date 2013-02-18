# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

import sys
from conda.config import Config


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'info',
        description     = "Display information about current Anaconda install.",
        help            = "Display information about current Anaconda install.",
    )
    els_group = p.add_mutually_exclusive_group()
    els_group.add_argument(
        '-e', "--envs",
        action  = "store_true",
        default = False,
        help    = "list all known Anaconda environments.",
    )
    els_group.add_argument(
        "--license",
        action  = "store_true",
        default = False,
        help    = "display information about local Anaconda licenses list",
    )
    els_group.add_argument(
        "--locations",
        action  = "store_true",
        default = False,
        help    = "list known locations for Anaconda environments.",
    )
    els_group.add_argument(
        '-s', "--system",
        action = "store_true",
        default = False,
        help = "list PATH and PYTHONPATH environments for debugging purposes",
    )
    p.set_defaults(func=execute)


def execute(args, parser):

    conf = Config()

    if args.envs:
        env_paths = conf.environment_paths

        if len(env_paths) == 0:
            print "No known environments in Anaconda locations"
            return

        print "Known Anaconda environments:"
        print

        for path in env_paths:
            print "    %s" % path
        print

    elif args.license:
        try:
            from _license import show_info
            show_info()
        except:
            raise RuntimeError("no function _license.show_info")

    elif args.locations:

        if len(conf.locations) == 0:
            print "No Anaconda locations configured"
            return

        print
        print "Locations for Anaconda environments:"
        print
        for location in conf.locations:
            print "    %s" % location,
            if location == conf.system_location:
                print " (system location)",
            print
        print

    elif args.system:

        import os

        print
        print "PATH: %s\n" % os.environ.get('PATH', None)
        print "PYTHONPATH: %s" % os.environ.get('PYTHONPATH', None)
        print

    else:
        print
        print "Current Anaconda install:"
        print conf
        print

