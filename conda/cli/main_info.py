# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import json
import os
import re
import sys
from collections import OrderedDict
from os import listdir
from os.path import exists, expanduser, join

from conda.config import rc_path
from conda.config import user_rc_path, sys_rc_path
from .common import (add_parser_json, stdout_json, disp_features, arg2spec,
                     handle_envs_list, add_parser_offline)
from ..compat import itervalues
from ..utils import on_win

help = "Display information about current conda install."

example = """

Examples:

    conda info -a
"""

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'info',
        description=help,
        help=help,
        epilog=example,
    )
    add_parser_json(p)
    add_parser_offline(p)
    p.add_argument(
        '-a', "--all",
        action="store_true",
        help="Show all information, (environments, license, and system "
             "information.")
    p.add_argument(
        '-e', "--envs",
        action="store_true",
        help="List all known conda environments.",
    )
    p.add_argument(
        '-l', "--license",
        action="store_true",
        help="Display information about the local conda licenses list.",
    )
    p.add_argument(
        '-s', "--system",
        action="store_true",
        help="List environment variables.",
    )
    p.add_argument(
        'packages',
        action="store",
        nargs='*',
        help="Display information about packages.",
    )
    p.add_argument(
        '--root',
        action='store_true',
        help='Display root environment path.',
    )
    p.add_argument(
        '--unsafe-channels',
        action='store_true',
        help='Display list of channels with tokens exposed.',
    )
    p.set_defaults(func=execute)


def show_pkg_info(name):
    from conda.api import get_index
    from conda.resolve import Resolve

    index = get_index()
    r = Resolve(index)
    print(name)
    if name in r.groups:
        for pkg in sorted(r.get_pkgs(name)):
            print('    %-15s %15s  %s' % (
                    pkg.version,
                    pkg.build,
                    disp_features(r.features(pkg.fn))))
    else:
        print('    not available')
    # TODO


python_re = re.compile('python\d\.\d')
def get_user_site():
    site_dirs = []
    if not on_win:
        if exists(expanduser('~/.local/lib')):
            for path in listdir(expanduser('~/.local/lib/')):
                if python_re.match(path):
                    site_dirs.append("~/.local/lib/%s" % path)
    else:
        if 'APPDATA' not in os.environ:
            return site_dirs
        APPDATA = os.environ['APPDATA']
        if exists(join(APPDATA, 'Python')):
            site_dirs = [join(APPDATA, 'Python', i) for i in
                         listdir(join(APPDATA, 'PYTHON'))]
    return site_dirs


def pretty_package(pkg):
    from conda.utils import human_bytes
    from conda.entities.channel import Channel

    d = OrderedDict([
        ('file name', pkg.fn),
        ('name', pkg.name),
        ('version', pkg.version),
        ('build number', pkg.build_number),
        ('build string', pkg.build),
        ('channel', Channel(pkg.channel).canonical_name),
        ('size', human_bytes(pkg.info['size'])),
        ])
    rest = pkg.info
    for key in sorted(rest):
        if key in {'build', 'depends', 'requires', 'channel', 'name',
                   'version', 'build_number', 'size'}:
            continue
        d[key] = rest[key]

    print()
    header = "%s %s %s" % (d['name'], d['version'], d['build string'])
    print(header)
    print('-'*len(header))
    for key in d:
        print("%-12s: %s" % (key, d[key]))
    print('dependencies:')
    for dep in pkg.info['depends']:
        print('    %s' % dep)

def execute(args, parser):
    import os
    from os.path import dirname

    import conda
    from conda.base.context import context
    from conda.entities.channel import offline_keep
    from conda.resolve import Resolve
    from conda.api import get_index

    if args.root:
        if args.json:
            stdout_json({'root_prefix': context.root_dir})
        else:
            print(context.root_dir)
        return

    if args.packages:
        index = get_index()
        r = Resolve(index)
        if args.json:
            stdout_json({
                package: [p._asdict()
                          for p in sorted(r.get_pkgs(arg2spec(package)))]
                for package in args.packages
            })
        else:
            for package in args.packages:
                versions = r.get_pkgs(arg2spec(package))
                for pkg in sorted(versions):
                    pretty_package(pkg)
        return

    options = 'envs', 'system', 'license'

    try:
        from conda.install import linked_data
        root_pkgs = linked_data(sys.prefix)
    except:
        root_pkgs = None

    try:
        import requests
        requests_version = requests.__version__
    except ImportError:
        requests_version = "could not import"
    except Exception as e:
        requests_version = "Error %s" % e

    try:
        cenv = [p for p in itervalues(root_pkgs) if p['name'] == 'conda-env']
        conda_env_version = cenv[0]['version']
    except:
        conda_env_version = "not installed"

    try:
        import conda_build
    except ImportError:
        conda_build_version = "not installed"
    except Exception as e:
        conda_build_version = "Error %s" % e
    else:
        conda_build_version = conda_build.__version__

    channels = context.channels

    if args.unsafe_channels:
        if not args.json:
            print("\n".join(channels))
        else:
            print(json.dumps({"channels": channels}))
        return 0

    channels = list(channels)
    if not args.json:
        channels = [c + ('' if offline_keep(c) else '  (offline)')
                    for c in channels]

    info_dict = dict(
        platform=context.subdir,
        conda_version=conda.__version__,
        conda_env_version=conda_env_version,
        conda_build_version=conda_build_version,
        root_prefix=context.root_dir,
        conda_prefix=context.conda_prefix,
        conda_private=context.conda_private,
        root_writable=context.root_writable,
        pkgs_dirs=context.pkgs_dirs,
        envs_dirs=context.envs_dirs,
        default_prefix=context.default_prefix,
        channels=channels,
        rc_path=rc_path,
        user_rc_path=user_rc_path,
        sys_rc_path=sys_rc_path,
        # is_foreign=bool(foreign),
        offline=context.offline,
        envs=[],
        python_version='.'.join(map(str, sys.version_info)),
        requests_version=requests_version,
    )

    if args.all or args.json:
        for option in options:
            setattr(args, option, True)

    if args.all or all(not getattr(args, opt) for opt in options):
        for key in 'pkgs_dirs', 'envs_dirs', 'channels':
            info_dict['_' + key] = ('\n' + 26 * ' ').join(info_dict[key])
        info_dict['_rtwro'] = ('writable' if info_dict['root_writable'] else
                               'read only')
        print("""\
Current conda install:

               platform : %(platform)s
          conda version : %(conda_version)s
       conda is private : %(conda_private)s
      conda-env version : %(conda_env_version)s
    conda-build version : %(conda_build_version)s
         python version : %(python_version)s
       requests version : %(requests_version)s
       root environment : %(root_prefix)s  (%(_rtwro)s)
    default environment : %(default_prefix)s
       envs directories : %(_envs_dirs)s
          package cache : %(_pkgs_dirs)s
           channel URLs : %(_channels)s
            config file : %(rc_path)s
           offline mode : %(offline)s
""" % info_dict)

    if args.envs:
        handle_envs_list(info_dict['envs'], not args.json)

    if args.system and not args.json:
        from conda.cli.find_commands import find_commands, find_executable

        print("sys.version: %s..." % (sys.version[:40]))
        print("sys.prefix: %s" % sys.prefix)
        print("sys.executable: %s" % sys.executable)
        print("conda location: %s" % dirname(conda.__file__))
        for cmd in sorted(set(find_commands() + ['build'])):
            print("conda-%s: %s" % (cmd, find_executable('conda-' + cmd)))
        print("user site dirs: ", end='')
        site_dirs = get_user_site()
        if site_dirs:
            print(site_dirs[0])
        else:
            print()
        for site_dir in site_dirs[1:]:
            print('                %s' % site_dir)
        print()

        evars = ['PATH', 'PYTHONPATH', 'PYTHONHOME', 'CONDA_DEFAULT_ENV',
                 'CIO_TEST', 'CONDA_ENVS_PATH']
        if context.platform == 'linux':
            evars.append('LD_LIBRARY_PATH')
        elif context.platform == 'osx':
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
WARNING: could not import _license.show_info
# try:
# $ conda install -n root _license""")

    if args.json:
        stdout_json(info_dict)
