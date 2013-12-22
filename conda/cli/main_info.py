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
    p.add_argument(
        '-a', "--all",
        action  = "store_true",
        help    = "show all information, (environments, license, and system "
                  "information")
    p.add_argument(
        '-e', "--envs",
        action  = "store_true",
        help    = "list all known conda environments",
    )
    p.add_argument(
        '-l', "--license",
        action  = "store_true",
        help    = "display information about local conda licenses list",
    )
    p.add_argument(
        '-s', "--system",
        action = "store_true",
        help = "list environment variables",
    )
    p.add_argument(
        'pkg_names',
        metavar = 'package_name',
        action = "store",
        nargs = '*',
        help = "display information about packages",
    )
    p.set_defaults(func=execute)


def show_pkg_info(name):
    #import conda.install as install
    from conda.api import get_index
    from conda.resolve import MatchSpec, Resolve

    index = get_index()
    r = Resolve(index)
    print(name)
    if name in r.groups:
        for pkg in sorted(r.get_pkgs(MatchSpec(name))):
            print('    %-15s %15s  %s' % (
                    pkg.version,
                    r.index[pkg.fn]['build'],
                    common.disp_features(r.features(pkg.fn))))
    else:
        print('    not available on channels')
    # TODO


def execute(args, parser):
    if args.pkg_names:
        for pkg_name in args.pkg_names:
            show_pkg_info(pkg_name)
        return

    import os
    from os.path import basename, dirname, isdir, join

    import conda
    import conda.config as config
    from conda.cli.main_init import is_initialized

    options = 'envs', 'system', 'license'

    info_dict = dict(platform=config.subdir,
                     conda_version=conda.__version__,
                     root_prefix=config.root_dir,
                     root_writable=config.root_writable,
                     pkgs_dirs=config.pkgs_dirs,
                     envs_dirs=config.envs_dirs,
                     default_prefix=config.default_prefix,
                     channels=config.get_channel_urls(),
                     rc_path=config.rc_path,
                     is_foreign=bool(config.foreign),
                     envs=[])

    if args.all or args.json:
        for option in options:
            setattr(args, option, True)

    if args.all or all(not getattr(args, opt) for opt in options):
        for key in 'pkgs_dirs', 'envs_dirs', 'channels':
            info_dict['_' + key] = ('\n' + 24 * ' ').join(info_dict[key])
        info_dict['_rtwro'] = ('writable' if info_dict['root_writable'] else
                               'read only')
        print("""\
Current conda install:

             platform : %(platform)s
        conda version : %(conda_version)s
     root environment : %(root_prefix)s  (%(_rtwro)s)
  default environment : %(default_prefix)s
     envs directories : %(_envs_dirs)s
        package cache : %(_pkgs_dirs)s
         channel URLs : %(_channels)s
          config file : %(rc_path)s
    is foreign system : %(is_foreign)s
""" % info_dict)
        if not is_initialized():
            print("""\
# NOTE:
#     root directory '%s' uninitalized,
#     use 'conda init' to initialize.""" % config.root_dir)

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
        import sys

        print("sys.version: %s..." % (sys.version[:40]))
        print("sys.prefix: %s" % sys.prefix)
        print("sys.executable: %s" % sys.executable)
        print("conda location: %s" % dirname(conda.__file__))
        print()

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
            print("""\
WARNING: could import _license.show_info
# try:
# $ conda install -n root _license""")

    if args.json:
        common.stdout_json(info_dict)
