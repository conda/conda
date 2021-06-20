# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import OrderedDict
import json
from logging import getLogger
import os
from os.path import exists, expanduser, isfile, join
import re
import sys

from .common import print_envs_list, stdout_json
from .. import CONDA_PACKAGE_ROOT, __version__ as conda_version
from ..base.context import conda_in_private_env, context, env_name, sys_rc_path, user_rc_path
from ..common.compat import iteritems, itervalues, on_win, text_type
from ..common.url import mask_anaconda_token
from ..core.index import _supplement_index_with_system
from ..models.channel import all_channel_urls, offline_keep
from ..models.match_spec import MatchSpec
from ..utils import human_bytes

log = getLogger(__name__)


def get_user_site():  # pragma: no cover
    site_dirs = []
    try:
        if not on_win:
            if exists(expanduser('~/.local/lib')):
                python_re = re.compile(r'python\d\.\d')
                for path in os.listdir(expanduser('~/.local/lib/')):
                    if python_re.match(path):
                        site_dirs.append("~/.local/lib/%s" % path)
        else:
            if 'APPDATA' not in os.environ:
                return site_dirs
            APPDATA = os.environ[str('APPDATA')]
            if exists(join(APPDATA, 'Python')):
                site_dirs = [join(APPDATA, 'Python', i) for i in
                             os.listdir(join(APPDATA, 'PYTHON'))]
    except (IOError, OSError) as e:
        log.debug('Error accessing user site directory.\n%r', e)
    return site_dirs


IGNORE_FIELDS = {'files', 'auth', 'preferred_env', 'priority'}

SKIP_FIELDS = IGNORE_FIELDS | {'name', 'version', 'build', 'build_number',
                               'channel', 'schannel', 'size', 'fn', 'depends'}


def dump_record(pkg):
    return {k: v for k, v in iteritems(pkg.dump()) if k not in IGNORE_FIELDS}


def pretty_package(prec):

    pkg = dump_record(prec)
    d = OrderedDict([
        ('file name', prec.fn),
        ('name', pkg['name']),
        ('version', pkg['version']),
        ('build string', pkg['build']),
        ('build number', pkg['build_number']),
        ('channel', text_type(prec.channel)),
        ('size', human_bytes(pkg['size'])),
    ])
    for key in sorted(set(pkg.keys()) - SKIP_FIELDS):
        d[key] = pkg[key]

    print('')
    header = "%s %s %s" % (d['name'], d['version'], d['build string'])
    print(header)
    print('-'*len(header))
    for key in d:
        print("%-12s: %s" % (key, d[key]))
    print('dependencies:')
    for dep in pkg['depends']:
        print('    %s' % dep)


def print_package_info(packages):
    from ..core.subdir_data import SubdirData
    results = {}
    for package in packages:
        spec = MatchSpec(package)
        results[package] = tuple(SubdirData.query_all(spec))

    if context.json:
        stdout_json({package: results[package] for package in packages})
    else:
        for result in itervalues(results):
            for prec in result:
                pretty_package(prec)

    print("WARNING: 'conda info package_name' is deprecated.\n"
          "          Use 'conda search package_name --info'.",
          file=sys.stderr)


def get_info_dict(system=False):
    try:
        from requests import __version__ as requests_version
        # These environment variables can influence requests' behavior, along with configuration
        # in a .netrc file
        #   CURL_CA_BUNDLE
        #   REQUESTS_CA_BUNDLE
        #   HTTP_PROXY
        #   HTTPS_PROXY
    except ImportError:  # pragma: no cover
        try:
            from pip._vendor.requests import __version__ as requests_version
        except Exception as e:  # pragma: no cover
            requests_version = "Error %r" % e
    except Exception as e:  # pragma: no cover
        requests_version = "Error %r" % e

    try:
        from conda_env import __version__ as conda_env_version
    except Exception:  # pragma: no cover
        conda_env_version = "not installed"

    try:
        import conda_build
    except ImportError:  # pragma: no cover
        conda_build_version = "not installed"
    except Exception as e:  # pragma: no cover
        conda_build_version = "Error %s" % e
    else:  # pragma: no cover
        conda_build_version = conda_build.__version__

    virtual_pkg_index = {}
    _supplement_index_with_system(virtual_pkg_index)
    virtual_pkgs = [[p.name, p.version, p.build] for p in virtual_pkg_index.values()]

    channels = list(all_channel_urls(context.channels))
    if not context.json:
        channels = [c + ('' if offline_keep(c) else '  (offline)')
                    for c in channels]
    channels = [mask_anaconda_token(c) for c in channels]

    netrc_file = os.environ.get('NETRC')
    if not netrc_file:
        user_netrc = expanduser("~/.netrc")
        if isfile(user_netrc):
            netrc_file = user_netrc

    active_prefix_name = env_name(context.active_prefix)

    info_dict = dict(
        platform=context.subdir,
        conda_version=conda_version,
        conda_env_version=conda_env_version,
        conda_build_version=conda_build_version,
        root_prefix=context.root_prefix,
        conda_prefix=context.conda_prefix,
        conda_private=conda_in_private_env(),
        av_data_dir=context.av_data_dir,
        av_metadata_url_base=context.signing_metadata_url_base,
        root_writable=context.root_writable,
        pkgs_dirs=context.pkgs_dirs,
        envs_dirs=context.envs_dirs,
        default_prefix=context.default_prefix,
        active_prefix=context.active_prefix,
        active_prefix_name=active_prefix_name,
        conda_shlvl=context.shlvl,
        channels=channels,
        user_rc_path=user_rc_path,
        rc_path=user_rc_path,
        sys_rc_path=sys_rc_path,
        # is_foreign=bool(foreign),
        offline=context.offline,
        envs=[],
        python_version='.'.join(map(str, sys.version_info)),
        requests_version=requests_version,
        user_agent=context.user_agent,
        conda_location=CONDA_PACKAGE_ROOT,
        config_files=context.config_files,
        netrc_file=netrc_file,
        virtual_pkgs=virtual_pkgs,
    )
    if on_win:
        from ..common._os.windows import is_admin_on_windows
        info_dict['is_windows_admin'] = is_admin_on_windows()
    else:
        info_dict['UID'] = os.geteuid()
        info_dict['GID'] = os.getegid()

    env_var_keys = {
        'CIO_TEST',
        'CURL_CA_BUNDLE',
        'REQUESTS_CA_BUNDLE',
        'SSL_CERT_FILE',
    }

    # add all relevant env vars, e.g. startswith('CONDA') or endswith('PATH')
    env_var_keys.update(v for v in os.environ if v.upper().startswith('CONDA'))
    env_var_keys.update(v for v in os.environ if v.upper().startswith('PYTHON'))
    env_var_keys.update(v for v in os.environ if v.upper().endswith('PATH'))
    env_var_keys.update(v for v in os.environ if v.upper().startswith('SUDO'))

    env_vars = {ev: os.getenv(ev, os.getenv(ev.lower(), '<not set>')) for ev in env_var_keys}

    proxy_keys = (v for v in os.environ if v.upper().endswith('PROXY'))
    env_vars.update({ev: '<set>' for ev in proxy_keys})

    info_dict.update({
        'sys.version': sys.version,
        'sys.prefix': sys.prefix,
        'sys.executable': sys.executable,
        'site_dirs': get_user_site(),
        'env_vars': env_vars,
    })

    return info_dict


def get_env_vars_str(info_dict):
    from textwrap import wrap
    builder = []
    builder.append("%23s:" % "environment variables")
    env_vars = info_dict.get('env_vars', {})
    for key in sorted(env_vars):
        value = wrap(env_vars[key])
        first_line = value[0] if len(value) else ""
        other_lines = value[1:] if len(value) > 1 else ()
        builder.append("%25s=%s" % (key, first_line))
        for val in other_lines:
            builder.append(' ' * 26 + val)
    return '\n'.join(builder)


def get_main_info_str(info_dict):
    for key in 'pkgs_dirs', 'envs_dirs', 'channels', 'config_files':
        info_dict['_' + key] = ('\n' + 26 * ' ').join(info_dict[key])

    info_dict['_virtual_pkgs'] = ('\n' + 26 * ' ').join([
        '%s=%s=%s' % tuple(x) for x in info_dict['virtual_pkgs']])
    info_dict['_rtwro'] = ('writable' if info_dict['root_writable'] else 'read only')

    format_param = lambda nm, val: "%23s : %s" % (nm, val)

    builder = ['']

    if info_dict['active_prefix_name']:
        builder.append(format_param('active environment', info_dict['active_prefix_name']))
        builder.append(format_param('active env location', info_dict['active_prefix']))
    else:
        builder.append(format_param('active environment', info_dict['active_prefix']))

    if info_dict['conda_shlvl'] >= 0:
        builder.append(format_param('shell level', info_dict['conda_shlvl']))

    builder.extend((
        format_param('user config file', info_dict['user_rc_path']),
        format_param('populated config files', info_dict['_config_files']),
        format_param('conda version', info_dict['conda_version']),
        format_param('conda-build version', info_dict['conda_build_version']),
        format_param('python version', info_dict['python_version']),
        format_param('virtual packages', info_dict['_virtual_pkgs']),
        format_param('base environment', '%s  (%s)' % (info_dict['root_prefix'],
                                                       info_dict['_rtwro'])),
        format_param('conda av data dir', info_dict['av_data_dir']),
        format_param('conda av metadata url', info_dict['av_metadata_url_base']),
        format_param('channel URLs', info_dict['_channels']),
        format_param('package cache', info_dict['_pkgs_dirs']),
        format_param('envs directories', info_dict['_envs_dirs']),
        format_param('platform', info_dict['platform']),
        format_param('user-agent', info_dict['user_agent']),
    ))

    if on_win:
        builder.append(format_param("administrator", info_dict['is_windows_admin']))
    else:
        builder.append(format_param("UID:GID", '%s:%s' % (info_dict['UID'], info_dict['GID'])))

    builder.extend((
        format_param('netrc file', info_dict['netrc_file']),
        format_param('offline mode', info_dict['offline']),
    ))

    builder.append('')
    return '\n'.join(builder)


def execute(args, parser):
    if args.base:
        if context.json:
            stdout_json({'root_prefix': context.root_prefix})
        else:
            print('{}'.format(context.root_prefix))
        return

    if args.packages:
        from ..resolve import ResolvePackageNotFound
        try:
            print_package_info(args.packages)
            return
        except ResolvePackageNotFound as e:  # pragma: no cover
            from ..exceptions import PackagesNotFoundError
            raise PackagesNotFoundError(e.bad_deps)

    if args.unsafe_channels:
        if not context.json:
            print("\n".join(context.channels))
        else:
            print(json.dumps({"channels": context.channels}))
        return 0

    options = 'envs', 'system'

    if args.all or context.json:
        for option in options:
            setattr(args, option, True)
    info_dict = get_info_dict(args.system)

    if (args.all or all(not getattr(args, opt) for opt in options)) and not context.json:
        stdout_logger = getLogger("conda.stdoutlog")
        stdout_logger.info(get_main_info_str(info_dict))
        stdout_logger.info("\n")

    if args.envs:
        from ..core.envs_manager import list_all_known_prefixes
        info_dict['envs'] = list_all_known_prefixes()
        print_envs_list(info_dict['envs'], not context.json)

    if args.system:
        if not context.json:
            from .find_commands import find_commands, find_executable
            print("sys.version: %s..." % (sys.version[:40]))
            print("sys.prefix: %s" % sys.prefix)
            print("sys.executable: %s" % sys.executable)
            print("conda location: %s" % info_dict['conda_location'])
            for cmd in sorted(set(find_commands() + ('build',))):
                print("conda-%s: %s" % (cmd, find_executable('conda-' + cmd)))
            print("user site dirs: ", end='')
            site_dirs = info_dict['site_dirs']
            if site_dirs:
                print(site_dirs[0])
            else:
                print('')
            for site_dir in site_dirs[1:]:
                print('                %s' % site_dir)
            print('')

            for name, value in sorted(iteritems(info_dict['env_vars'])):
                print("%s: %s" % (name, value))
            print('')

    if context.json:
        stdout_json(info_dict)
