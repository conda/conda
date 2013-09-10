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

log = logging.getLogger(__name__)


default_python = '3.3' if PY3 else '2.7'
default_numpy = '1.7'

# ----- constant paths -----

root_dir = os.getenv('CONDA_ROOT', sys.prefix)
pkgs_dir = os.getenv('CONDA_PACKAGE_CACHE', join(root_dir, 'pkgs'))
envs_dir = os.getenv('CONDA_ENV_PATH', join(root_dir, 'envs'))

_user_root_dir = os.getenv('CONDA_USER_ROOT', join(expanduser('~'), 'conda'))
user_pkgs_dir = os.getenv('CONDA_USER_PACKAGE_CACHE', join(_user_root_dir, 'pkgs'))
user_envs_dir = os.getenv('CONDA_USER_ENV_PATH', join(_user_root_dir, 'envs'))

system_pkgs_dir = pkgs_dir
system_envs_dir = envs_dir


# Check to see if we can write to a particular directory
def test_write(direc):
    tmpname = "_conda_test_file.delme"
    test_write = "A test string"
    fname = join(direc, tmpname)
    try:
        with open(fname, 'wb') as f:
            f.write(test_write)
        os.unlink(fname)
        return True
    except:
        return False

# Setup config variables to point to user_variables if
#  not writeable
#  FIXME:  This may fail if user_pkgs_dir or user_envs_dir is still not
#          writeable.
if not test_write(pkgs_dir):
    if not os.path.exists(user_pkgs_dir):
        os.makedirs(user_pkgs_dir)
    pkgs_dir = user_pkgs_dir

if not test_write(envs_dir):
    if not os.path.exists(user_envs_dir):
        os.makedirs(user_envs_dir)
    envs_dir = user_envs_dir

usermode = (pkgs_dir != system_pkgs_dir) or (envs_dir != system_envs_dir)

# Usermode affects a few commands (FIXME -- not implemented yet)
# conda create (new environments created in envs_dir by default)
# conda install (packages should be linked from system if available or
#                 downloaded to user_pkgs_dir)
#   FIXME:  really the pkgs directory should be a list of available
#           cache directories to use to link environments to and always
#           be treated as a list (with only the first entry assumed writeable)
# conda info (states whether usermode is enabled and lists system and user)
# conda update (same as install)
# conda clean (FIXME:  What do we do about dangling environments that are
#                      unkown to the system --- i.e. this command could remove
#                      packages that other usermode environments need)
#       
# Possible partial proposal: the conda-meta directory in every file should 
#           contain a file that maps the packages defined in the environment 
#           to which pkgs directory it came from

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


def get_rc_proxy_servers():
    return rc.get('proxy_servers',None)

def get_proxy_servers():
    if 'proxy_servers' not in rc:
        proxy_servers = None
    else:
        proxy_servers = get_rc_proxy_servers()
    return proxy_servers
