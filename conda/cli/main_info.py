# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import re
import sys
from os.path import isfile
from collections import defaultdict

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
        'args',
        metavar = 'args',
        action = "store",
        nargs = '*',
        help = "display information about packages or files",
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
                    pkg.build,
                    common.disp_features(r.features(pkg.fn))))
    else:
        print('    not available on channels')
    # TODO


def execute(args, parser):
    import os
    from os.path import basename, dirname, isdir, join

    import conda
    import conda.config as config
    import conda.misc as misc
    from conda.cli.main_init import is_initialized
    from conda.api import get_package_versions, app_is_installed
    from conda.install import is_linked

    if args.args:
        results = defaultdict(list)

        for arg in args.args:
            if isfile(arg):
                from conda.misc import which_package
                path = arg
                for dist in which_package(path):
                    if args.json:
                        results[arg].append(dist)
                    else:
                        print('%-50s  %s' % (path, dist))
            elif arg.endswith('.tar.bz2'):
                info = None
                for prefix in misc.list_prefixes():
                    info = is_linked(prefix, arg[:-8])
                    if info:
                        break

                if not info:
                    if args.json:
                        results[arg] = {
                            'installed': []
                        }
                    else:
                        print("Package %s is not installed" % arg)

                    continue

                info['installed'] = app_is_installed(arg)
                if args.json:
                    results[arg] = info
                else:
                    print(arg)
                    print('    %-15s %30s' %
                               ('installed', bool(info.get('installed'))))

                    for key in ('name', 'version', 'build', 'license',
                                'platform', 'arch', 'size', 'summary'):
                        print('    %-15s %30s' % (key, info.get(key)))
            else:
                if args.json:
                    for pkg in get_package_versions(arg):
                        results[arg].append(pkg._asdict())
                else:
                    show_pkg_info(arg)

        if args.json:
            common.stdout_json(results)
        return

    options = 'envs', 'system', 'license'

    try:
        import requests
        requests_version = requests.__version__
    except ImportError:
        requests_version = "could not import"
    except Exception as e:
        requests_version = "Error %s" % e

    try:
        import conda_build
    except ImportError:
        conda_build_version = "not installed"
    except Exception as e:
        conda_build_version = "Error %s" % e
    else:
        conda_build_version = conda_build.__version__

    info_dict = dict(platform=config.subdir,
                     conda_version=conda.__version__,
                     conda_build_version=conda_build_version,
                     root_prefix=config.root_dir,
                     root_writable=config.root_writable,
                     pkgs_dirs=config.pkgs_dirs,
                     envs_dirs=config.envs_dirs,
                     default_prefix=config.default_prefix,
                     channels=config.get_channel_urls(),
                     rc_path=config.rc_path,
                     is_foreign=bool(config.foreign),
                     envs=[],
                     python_version='.'.join(map(str, sys.version_info)),
                     requests_version=requests_version,
    )

    if args.all or args.json:
        for option in options:
            setattr(args, option, True)

    t_pat = re.compile(r'binstar\.org/(t/[0-9a-zA-Z\-]{4,})')
    info_dict['channels_disp'] = [t_pat.sub('binstar.org/t/<TOKEN>', c)
                                  for c in info_dict['channels']]

    if args.all or all(not getattr(args, opt) for opt in options):
        for key in 'pkgs_dirs', 'envs_dirs', 'channels_disp':
            info_dict['_' + key] = ('\n' + 24 * ' ').join(info_dict[key])
        info_dict['_rtwro'] = ('writable' if info_dict['root_writable'] else
                               'read only')
        print("""\
Current conda install:

             platform : %(platform)s
        conda version : %(conda_version)s
  conda-build version : %(conda_build_version)s
       python version : %(python_version)s
     requests version : %(requests_version)s
     root environment : %(root_prefix)s  (%(_rtwro)s)
  default environment : %(default_prefix)s
     envs directories : %(_envs_dirs)s
        package cache : %(_pkgs_dirs)s
         channel URLs : %(_channels_disp)s
          config file : %(rc_path)s
    is foreign system : %(is_foreign)s
""" % info_dict)
        if not is_initialized():
            print("""\
# NOTE:
#     root directory '%s' uninitalized,
#     use 'conda init' to initialize.""" % config.root_dir)

    del info_dict['channels_disp']

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

        for prefix in misc.list_prefixes():
            disp_env(prefix)
            if prefix != config.root_dir:
                info_dict['envs'].append(prefix)

        print()

    if args.system and not args.json:
        from conda.cli.find_commands import find_commands, find_executable

        print("sys.version: %s..." % (sys.version[:40]))
        print("sys.prefix: %s" % sys.prefix)
        print("sys.executable: %s" % sys.executable)
        print("conda location: %s" % dirname(conda.__file__))
        for cmd in sorted(set(find_commands() + ['build'])):
            print("conda-%s: %s" % (cmd, find_executable(cmd)))
        print()

        evars = ['PATH', 'PYTHONPATH', 'PYTHONHOME', 'CONDA_DEFAULT_ENV',
                 'CIO_TEST', 'CONDA_ENVS_PATH']
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
