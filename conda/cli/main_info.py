# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

import os
import sys
from conda.config import Config


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'info',
        description     = "Display information about current conda install.",
        help            = "Display information about current conda install.",
    )
    els_group = p.add_mutually_exclusive_group()
    els_group.add_argument(
        '-a', "--all",
        action  = "store_true",
        default = False,
        help    = "show location, license, and system information.")
    els_group.add_argument(
        '-e', "--envs",
        action  = "store_true",
        default = False,
        help    = "list all known conda environments.",
    )
    els_group.add_argument(
        "--license",
        action  = "store_true",
        default = False,
        help    = "display information about local conda licenses list",
    )
    els_group.add_argument(
        "--locations",
        action  = "store_true",
        default = False,
        help    = "list known locations for conda environments.",
    )
    els_group.add_argument(
        '-s', "--system",
        action = "store_true",
        default = False,
        help = "list PATH and PYTHONPATH environments for debugging purposes",
    )
    p.set_defaults(func=execute)


def execute(args, parser):

    options = ['envs', 'locations', 'system', 'license']

    conf = Config()

    if args.all:
        for option in options:
            setattr(args, option, True)

    if args.all or all(not getattr(args, opt) for opt in options):
        print
        print "Current conda install:"
        print conf

    if args.locations:
        if len(conf.locations) == 0:
            print "No conda locations configured"
        else:
            print
            print "Locations for conda environments:"
            print
            for location in conf.locations:
                print "    %s" % location,
                if location == conf.system_location:
                    print " (system location)",
                print
            print

    if args.envs:
        env_paths = conf.environment_paths

        if len(env_paths) == 0:
            print "Known conda environments: None"
        else:
            print "Known conda environments:"
            print
            for path in env_paths:
                print "    %s" % path
            print

    if args.system:
        print
        print "PATH: %s" % os.getenv('PATH')
        print "PYTHONPATH: %s" % os.getenv('PYTHONPATH')
        if sys.platform == 'linux':
            print "LD_LIBRARY_PATH: %s" % os.getenv('LD_LIBRARY_PATH')
        elif sys.platform == 'darwin':
            print "DYLD_LIBRARY_PATH: %s" % os.getenv('DYLD_LIBRARY_PATH')
        print "CONDA_DEFAULT_ENV: %s" % os.getenv('CONDA_DEFAULT_ENV')
        print

    if args.license:
        try:
            from _license import show_info
            show_info()
        except ImportError:
            print("WARNING: could import _license.show_info,\n"
                  "         try: conda install _license")
