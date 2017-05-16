# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import absolute_import, division, print_function, unicode_literals

from collections import OrderedDict
import json
from logging import getLogger
import os
from os import listdir
from os.path import exists, expanduser, isfile, join
import re
import sys

from .common import add_parser_json, add_parser_offline, arg2spec, handle_envs_list, stdout_json
from ..common.compat import iteritems, itervalues, on_win

log = getLogger(__name__)

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


def get_user_site():
    site_dirs = []
    try:
        if not on_win:
            if exists(expanduser('~/.local/lib')):
                python_re = re.compile('python\d\.\d')
                for path in listdir(expanduser('~/.local/lib/')):
                    if python_re.match(path):
                        site_dirs.append("~/.local/lib/%s" % path)
        else:
            if 'APPDATA' not in os.environ:
                return site_dirs
            APPDATA = os.environ[str('APPDATA')]
            if exists(join(APPDATA, 'Python')):
                site_dirs = [join(APPDATA, 'Python', i) for i in
                             listdir(join(APPDATA, 'PYTHON'))]
    except (IOError, OSError) as e:
        log.debug('Error accessing user site directory.\n%r', e)
    return site_dirs


IGNORE_FIELDS = {'files', 'auth', 'with_features_depends',
                 'preferred_env', 'priority'}

SKIP_FIELDS = IGNORE_FIELDS | {'name', 'version', 'build', 'build_number',
                               'channel', 'schannel', 'size', 'fn', 'depends'}


def dump_record(pkg):
    return {k: v for k, v in iteritems(pkg.dump()) if k not in IGNORE_FIELDS}


def pretty_package(dist, pkg):
    from ..utils import human_bytes

    pkg = dump_record(pkg)
    d = OrderedDict([
        ('file name', dist.to_filename()),
        ('name', pkg['name']),
        ('version', pkg['version']),
        ('build string', pkg['build']),
        ('build number', pkg['build_number']),
        ('channel', dist.channel),
        ('size', human_bytes(pkg['size'])),
    ])
    for key in sorted(set(pkg.keys()) - SKIP_FIELDS):
        d[key] = pkg[key]

    print()
    header = "%s %s %s" % (d['name'], d['version'], d['build string'])
    print(header)
    print('-'*len(header))
    for key in d:
        print("%-12s: %s" % (key, d[key]))
    print('dependencies:')
    for dep in pkg['depends']:
        print('    %s' % dep)


def print_package_info(packages):
    from ..api import get_index
    from ..base.context import context
    from ..resolve import Resolve
    index = get_index()
    r = Resolve(index)
    if context.json:
        stdout_json({
            package: [dump_record(r.index[d])
                      for d in r.get_dists_for_spec(arg2spec(package))]
            for package in packages
        })
    else:
        for package in packages:
            for dist in r.get_dists_for_spec(arg2spec(package)):
                pretty_package(dist, r.index[dist])


def get_info_dict(system=False):
    from .. import CONDA_PACKAGE_ROOT, __version__ as conda_version
    from ..base.context import context
    from ..common.url import mask_anaconda_token
    from ..config import rc_path, sys_rc_path, user_rc_path
    from ..connection import user_agent
    from ..models.channel import offline_keep, prioritize_channels

    try:
        from ..install import linked_data
        root_pkgs = linked_data(context.root_prefix)
    except:
        root_pkgs = None

    try:
        from requests import __version__ as requests_version
        # These environment variables can influence requests' behavior, along with configuration
        # in a .netrc file
        #   REQUESTS_CA_BUNDLE
        #   HTTP_PROXY
        #   HTTPS_PROXY
    except ImportError:
        requests_version = "could not import"
    except Exception as e:
        requests_version = "Error %r" % e

    try:
        from conda_env import __version__ as conda_env_version
    except:
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

    channels = list(prioritize_channels(context.channels).keys())
    if not context.json:
        channels = [c + ('' if offline_keep(c) else '  (offline)')
                    for c in channels]
    channels = [mask_anaconda_token(c) for c in channels]

    netrc_file = os.environ.get('NETRC')
    if not netrc_file:
        user_netrc = expanduser("~/.netrc")
        if isfile(user_netrc):
            netrc_file = user_netrc

    info_dict = dict(
        platform=context.subdir,
        conda_version=conda_version,
        conda_env_version=conda_env_version,
        conda_build_version=conda_build_version,
        root_prefix=context.root_prefix,
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
        user_agent=user_agent,
        conda_location=CONDA_PACKAGE_ROOT,
        netrc_file=netrc_file,
    )
    if on_win:
        from ..common.platform import is_admin_on_windows
        info_dict['is_windows_admin'] = is_admin_on_windows()
    else:
        info_dict['UID'] = os.geteuid()
        info_dict['GID'] = os.getegid()

    if system:
        evars = ['PATH', 'PYTHONPATH', 'PYTHONHOME', 'CONDA_DEFAULT_ENV',
                 'CIO_TEST', 'CONDA_ENVS_PATH']

        if context.platform == 'linux':
            evars.append('LD_LIBRARY_PATH')
        elif context.platform == 'osx':
            evars.append('DYLD_LIBRARY_PATH')

        info_dict.update({
            'sys.version': sys.version,
            'sys.prefix': sys.prefix,
            'sys.executable': sys.executable,
            'site_dirs': get_user_site(),
            'env_vars': {ev: os.getenv(ev, '<not set>') for ev in evars},
        })

    return info_dict


def get_main_info_str(info_dict):
    from .._vendor.auxlib.ish import dals

    for key in 'pkgs_dirs', 'envs_dirs', 'channels':
        info_dict['_' + key] = ('\n' + 26 * ' ').join(info_dict[key])
    info_dict['_rtwro'] = ('writable' if info_dict['root_writable'] else 'read only')

    builder = []
    builder.append(dals("""
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
                 netrc file : %(netrc_file)s
               offline mode : %(offline)s
                 user-agent : %(user_agent)s\
    """) % info_dict)

    if on_win:
        builder.append("          administrator : %(is_windows_admin)s" % info_dict)
    else:
        builder.append("                UID:GID : %(UID)s:%(GID)s" % info_dict)

    return '\n'.join(builder)


def execute(args, parser):
    from ..base.context import context

    if args.root:
        if context.json:
            stdout_json({'root_prefix': context.root_prefix})
        else:
            print(context.root_prefix)
        return

    if args.packages:
        print_package_info(args.packages)
        return

    if args.unsafe_channels:
        if not context.json:
            print("\n".join(context.channels))
        else:
            print(json.dumps({"channels": context.channels}))
        return 0

    options = 'envs', 'system', 'license'

    if args.all or context.json:
        for option in options:
            setattr(args, option, True)

    info_dict = get_info_dict(args.system)

    if (args.all or all(not getattr(args, opt) for opt in options)) and not context.json:
        print(get_main_info_str(info_dict))

    if args.envs:
        handle_envs_list(info_dict['envs'], not context.json)

    if args.system:
        if not context.json:
            from .find_commands import find_commands, find_executable
            print("sys.version: %s..." % (sys.version[:40]))
            print("sys.prefix: %s" % sys.prefix)
            print("sys.executable: %s" % sys.executable)
            print("conda location: %s" % info_dict['conda_location'])
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

            for name, value in sorted(iteritems(info_dict['env_vars'])):
                print("%s: %s" % (name, value))
            print()

    if args.license and not context.json:
        try:
            from _license import show_info
            show_info()
        except ImportError:
            print("""\
WARNING: could not import _license.show_info
# try:
# $ conda install -n root _license""")

    if context.json:
        stdout_json(info_dict)
