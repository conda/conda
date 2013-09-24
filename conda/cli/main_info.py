# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

from conda.cli import common


help = "Display information about current conda install."


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser('info',
                               description = help,
                               help = help)
    common.add_parser_json(p)
    els_group = p.add_mutually_exclusive_group()
    els_group.add_argument(
        '-a', "--all",
        action  = "store_true",
        help    = "show all information, (environments, license, and system "
                  "information.")
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
        '-s', "--system",
        action = "store_true",
        help = "list environment variables",
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    import os
    from os.path import basename, dirname, isdir, join

    import conda
    import conda.config as config


    options = 'envs', 'system', 'license'

    info_dict = dict(platform=config.subdir,
                     conda_version=conda.__version__,
                     conda_location=dirname(conda.__file__),
                     root_prefix=config.root_dir,
                     pkgs_dirs=config.pkgs_dirs,
                     envs_dirs=config.envs_dirs,
                     default_prefix=config.default_prefix,
                     channels=config.get_channel_urls(),
                     rc_path=config.rc_path,
                     envs=[])

    if args.all or args.json:
        for option in options:
            setattr(args, option, True)

    if args.all or all(not getattr(args, opt) for opt in options):
        for key in 'pkgs_dirs', 'envs_dirs', 'channels':
            info_dict['_' + key] = ('\n' + 24 * ' ').join(info_dict[key])
        print("""\
Current conda install:

             platform : %(platform)s
        conda version : %(conda_version)s
       conda location : %(conda_location)s
     root environment : %(root_prefix)s
  default environment : %(default_prefix)s
     envs directories : %(_envs_dirs)s
        package cache : %(_pkgs_dirs)s
         channel URLs : %(_channels)s
          config file : %(rc_path)s
""" % info_dict)

    if args.envs:
        if not args.json:
            print("# conda environments:")
            print("#")
        def disp_env(prefix):
            fmt = '%-20s  %s  %s'
            default = '*' if prefix == config.default_prefix else ' '
            name = (config.root_env_name if prefix == config.root_dir else
                    basename(prefix))
            if not args.json:
                print(fmt % (name, default, prefix))

        for envs_dir in config.envs_dirs:
            if not isdir(envs_dir):
                continue
            for dn in sorted(os.listdir(envs_dir)):
                if dn.startswith('.'):
                    continue
                prefix = join(envs_dir, dn)
                if isdir(prefix):
                    prefix = join(envs_dir, dn)
                    disp_env(prefix)
                    info_dict['envs'].append(prefix)
        disp_env(config.root_dir)
        print()

    if args.system and not args.json:
        evars = ['PATH', 'PYTHONPATH', 'CONDA_DEFAULT_ENV', 'CIO_TEST',
                 'CONDA_ENVS_PATH']
        if config.platform == 'linux':
            evars.append('LD_LIBRARY_PATH')
        elif config.platform == 'osx':
            evars.append('DYLD_LIBRARY_PATH')
        for ev in sorted(evars):
            print("%s: %s" % (ev, os.getenv(ev, '<not set>')))
        print()

    if args.license and not args.json:
        try:
            from _license import show_info
            show_info()
        except ImportError:
            print("WARNING: could import _license.show_info,\n"
                  "         try: conda install _license")

    if args.json:
        common.stdout_json(info_dict)
