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
from os.path import abspath, dirname, expanduser, isfile, isdir, join

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
    'disallow',
    'create_default_packages',
    'track_features',
    'envs_dirs',
    ]

rc_bool_keys = [
    'always_yes',
    'changeps1',
    'use_pip',
    'binstar_upload',
    'binstar_personal',
    ]

# Not supported by conda config yet
rc_other = [
    'proxy_servers',
    'root_dir',
    'conda_recipes_dir',
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

    return yaml.load(open(path)) or {}

rc = load_condarc(rc_path)

wrong_keys = set(rc.keys()) - set(rc_list_keys + rc_bool_keys + rc_other)
if wrong_keys:
    print("Warning: Unrecognized key(s) in condarc (%s): %s" % (rc_path, wrong_keys))

# ----- local directories -----

root_dir = abspath(expanduser(os.getenv('CONDA_ROOT',
                                        rc.get('root_dir', sys.prefix))))
root_writable = try_write(root_dir)
root_env_name = 'root'

def _pathsep_env(name):
    x = os.getenv(name)
    if x:
        return x.split(os.pathsep)
    else:
        return []

def _default_envs_dirs():
    lst = [join(root_dir, 'envs')]
    if not root_writable:
        lst.insert(0, '~/envs')
    return lst

envs_dirs = [abspath(expanduser(path)) for path in (
        _pathsep_env('CONDA_ENVS_PATH') or
        rc.get('envs_dirs') or
        _default_envs_dirs()
        )]

def pkgs_dir_prefix(prefix):
    if (abspath(prefix) == root_dir or
            abspath(dirname(prefix)) == abspath(join(root_dir, 'envs'))):
        return join(root_dir, 'pkgs')
    else:
        return abspath(join(prefix, '..', '.pkgs'))

def set_pkgs_dirs(prefix=None):
    global pkgs_dirs

    pkgs_dirs = [pkgs_dir_prefix(prefix)] if prefix else []
    for envs_dir in envs_dirs:
        pkgs_dir = pkgs_dir_prefix(join(envs_dir, 'dummy'))
        if pkgs_dir not in pkgs_dirs:
            pkgs_dirs.append(pkgs_dir)

set_pkgs_dirs()

# ----- default environment prefix -----

_default_env = os.getenv('CONDA_DEFAULT_ENV')
if _default_env in (None, root_env_name):
    default_prefix = root_dir
elif os.sep in _default_env:
    default_prefix = abspath(_default_env)
else:
    for envs_dir in envs_dirs:
        default_prefix = join(envs_dir, _default_env)
        if isdir(default_prefix):
            break
    else:
        default_prefix = join(envs_dirs[0], _default_env)

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

def get_proxy_servers():
    res = rc.get('proxy_servers')
    if res is None or isinstance(res, dict):
        return res
    sys.exit("Error: proxy_servers setting not a mapping")

# ----- foreign -----

try:
    with open(join(root_dir, 'conda-meta', 'foreign')) as fi:
        foreign = fi.read().split()
except IOError:
    foreign = [] if isdir(join(root_dir, 'conda-meta')) else ['python']

# ----- misc -----

always_yes = rc.get('always_yes', False)
changeps1 = rc.get('changeps1', True)
use_pip = rc.get('use_pip', True)
binstar_upload = rc.get('binstar_upload', None) # None means ask
binstar_personal = rc.get('binstar_personal', True)
disallow = set(rc.get('disallow', []))
# packages which are added to a newly created environment by default
create_default_packages = list(rc.get('create_default_packages', []))
track_features = set(rc.get('track_features', '').split())

#======================================================================#
#====== CONDA_ADDONS:  https://github.com/peter1000/conda_addons ======#
#======================================================================#

conda_recipes_dir = rc.get('conda_recipes_dir', join(root_dir, 'conda-recipes'))
print("conda_recipes_dir: ", conda_recipes_dir)
