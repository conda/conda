# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import os
import sys
import logging
from platform import machine
from os.path import abspath, expanduser, isfile, join

from conda.compat import PY3
from conda.install import try_write


log = logging.getLogger(__name__)


default_python = '3.3' if PY3 else '2.7'
default_numpy = '1.7'

# ----- operating system and architecture -----

_sys_map = {'linux2': 'linux', 'linux': 'linux',
            'darwin': 'osx', 'win32': 'win'}
platform = _sys_map.get(sys.platform, 'unknown')
bits = 8 * tuple.__itemsize__

if platform == 'linux' and machine() == 'armv6l':
    subdir = 'linux-armv6l'
    arch_name = 'armv6l'
else:
    subdir = '%s-%d' % (platform, bits)
    arch_name = {64: 'x86_64', 32: 'x86'}[bits]

# ----- rc file -----

# This is used by conda config to check which keys are allowed in the config
# file. Be sure to update it when new keys are added.
rc_list_keys = [
    'channels',
    ]
rc_bool_keys = [
    'changeps1',
    'binstar_upload',
    ]

user_rc_path = abspath(expanduser('~/.condarc'))
sys_rc_path = join(sys.prefix, '.condarc')
def get_rc_path():
    for path in [user_rc_path, sys_rc_path]:
        if isfile(path):
            return path
    return None

rc_path = get_rc_path()

def load_condarc(path):
    if not path:
        return {}
    try:
        import yaml
    except ImportError:
        sys.exit('Error: could not import yaml (required to read .condarc '
                 'config file)')

    return yaml.load(open(path))

rc = load_condarc(rc_path)

# ----- local directories -----

def pathsep_env(name):
    x = os.getenv(name)
    if x:
        return x.split(os.pathsep)
    else:
        return []

root_dir = abspath(expanduser(os.getenv('CONDA_ROOT',
                                        rc.get('root_dir', sys.prefix))))

def default_pkgs_dirs():
    root_pkgs = join(root_dir, 'pkgs')
    if try_write(root_pkgs):
        return [root_pkgs]
    else:
        return [abspath(expanduser('~/conda')), root_pkgs]

pkgs_dirs = [abspath(expanduser(path)) for path in (
        pathsep_env('CONDA_PACKAGE_CACHE') or
        rc.get('pkgs_dirs') or
        default_pkgs_dirs()
        )]
envs_dirs = [abspath(expanduser(path)) for path in (
        pathsep_env('CONDA_ENV_PATH') or
        rc.get('envs_dirs') or
        [join(root_dir, 'envs')]
        )]

pkgs_dir = pkgs_dirs[0]
envs_dir = envs_dirs[0]

# ----- default environment prefix -----

_default_env = os.getenv('CONDA_DEFAULT_ENV')
if not _default_env:
    default_prefix = root_dir
elif os.sep in _default_env:
    default_prefix = abspath(_default_env)
else:
    default_prefix = join(envs_dir, _default_env)

# ----- misc -----

changeps1 = rc.get('changeps1', True)
binstar_upload = rc.get('binstar_upload', None) # None means ask

# ----- channels -----

# Note, get_default_urls() and get_rc_urls() return unnormalized urls.

def get_default_urls():
    return ['http://repo.continuum.io/pkgs/free',
            'http://repo.continuum.io/pkgs/pro']

def get_rc_urls():
    if 'system' in rc['channels']:
        raise RuntimeError("system cannot be used in .condarc")
    return rc['channels']

def normalize_urls(urls):
    newurls = []
    for url in urls:
        if url == "defaults":
            newurls.extend(normalize_urls(get_default_urls()))
        elif url == "system":
            if not rc_path:
                newurls.extend(normalize_urls(get_default_urls()))
            else:
                newurls.extend(normalize_urls(get_rc_urls()))
        else:
            newurls.append('%s/%s/' % (url.rstrip('/'), subdir))
    return newurls

def get_channel_urls():
    if os.getenv('CIO_TEST'):
        base_urls = ['http://filer/pkgs/pro',
                     'http://filer/pkgs/free']
        if os.getenv('CIO_TEST') == '2':
            base_urls.insert(0, 'http://filer/test-pkgs')

    elif 'channels' not in rc:
        base_urls = get_default_urls()

    else:
        base_urls = get_rc_urls()

    return normalize_urls(base_urls)

# ----- proxy -----

def get_rc_proxy_servers():
    return rc.get('proxy_servers',None)

def get_proxy_servers():
    if 'proxy_servers' not in rc:
        proxy_servers = None
    else:
        proxy_servers = get_rc_proxy_servers()
    return proxy_servers
