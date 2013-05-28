# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

import utils


descr = "Display information about current conda install."


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser('info',
                               description = descr,
                               help = descr)
    utils.add_parser_json(p)
    els_group = p.add_mutually_exclusive_group()
    els_group.add_argument(
        '-a', "--all",
        action  = "store_true",
        help    = "show location, license, and system information.")
    els_group.add_argument(
        '-e', "--envs",
        action  = "store_true",
        help    = "list all known conda environments.",
    )
    els_group.add_argument(
        "--license",
        action  = "store_true",
        help    = "display information about local conda licenses list",
    )
    els_group.add_argument(
        "--locations",
        action  = "store_true",
        help    = "list known locations for conda environments.",
    )
    els_group.add_argument(
        '-s', "--system",
        action = "store_true",
        help = "list PATH and PYTHONPATH environments for debugging purposes",
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    import os
    import sys
    import json

    import conda
    import conda.config as config

    options = ['envs', 'locations', 'system', 'license']

    info_dict = dict(platform=config.subdir,
                     conda_version=conda.__version__,
                     root_prefix=config.root_dir,
                     default_prefix=config.default_prefix,
                     channels=config.get_channel_urls(),
                     rc_path=config.rc_path)
    if args.json:
        json.dump(info_dict, sys.stdout, indent=2, sort_keys=True)
        return

    if args.all:
        for option in options:
            setattr(args, option, True)

    if args.all or all(not getattr(args, opt) for opt in options):
        info_dict['ppcs'] = ('\n' + 24 * ' ').join(info_dict['channels'])
        print """
Current conda install:

             platform : %(platform)s
conda command version : %(conda_version)s
       root directory : %(root_prefix)s
       default prefix : %(default_prefix)s
         channel URLs : %(ppcs)s
          config file : %(rc_path)s
""" % info_dict

    if 0:# TODO   args.locations:
        if len(config.locations) == 0:
            print "No conda locations configured"
        else:
            print
            print "Locations for conda environments:"
            print
            for location in config.locations:
                print "    %s" % location,
                if location == config.envs_dir:
                    print " (system location)",
                print
            print

    if 0:# TODO   args.envs:
        env_paths = config.environment_paths

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
        if config.platform == 'linux':
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
