# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

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

def get_rc_path():
    for path in [abspath(expanduser('~/.condarc')),
                 join(sys.prefix, '.condarc')]:
        if isfile(path):
            return path
    return None

rc_path = get_rc_path()

def load_condarc(path):
    import yaml

    return yaml.load(open(path))

rc = load_condarc(rc_path)

# ----- channels -----

# Note, get_default_urls() and get_rc_urls() return unnormalized urls.

def get_default_urls():
    base_urls = ['http://repo.continuum.io/pkgs/free',
                     'http://repo.continuum.io/pkgs/pro']
    if os.getenv('CIO_TEST'):
        base_urls = ['http://filer/pkgs/pro',
                     'http://filer/pkgs/free']
        if os.getenv('CIO_TEST') == '2':
            base_urls.insert(0, 'http://filer/test-pkgs')
    return base_urls

def get_rc_urls():
    if 'channels' not in rc:
        raise RuntimeError("config file '%s' is missing channels" %
                           rc_path)
    if 'rc' in rc['channels']:
        raise RuntimeError("rc cannot be used in .condarc")
    return rc['channels']

def get_channel_urls():
    from api import normalize_urls

    if rc_path is None:
        base_urls = get_default_urls()
    else:
        base_urls = get_rc_urls()

    return normalize_urls(base_urls)
