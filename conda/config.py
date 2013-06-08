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


log = logging.getLogger(__name__)


default_python = '2.7'
default_numpy = '1.7'

# ----- constant paths -----

root_dir = os.getenv('CONDA_ROOT', sys.prefix)
pkgs_dir = os.getenv('CONDA_PACKAGE_CACHE', join(root_dir, 'pkgs'))
envs_dir = os.getenv('CONDA_ENV_PATH', join(root_dir, 'envs'))

# ----- default environment prefix -----

_default_env = os.getenv('CONDA_DEFAULT_ENV')
if not _default_env:
    default_prefix = root_dir
elif os.sep in _default_env:
    default_prefix = abspath(_default_env)
else:
    default_prefix = join(envs_dir, _default_env)

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
    import yaml

    return yaml.load(open(path))

rc = load_condarc(rc_path)

changeps1 = rc.get('changeps1', True)

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
