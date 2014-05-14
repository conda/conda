# (c) 2012-2014 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import os
import sys
import logging
from platform import machine
from os.path import abspath, expanduser, isfile, isdir, join

from conda.compat import urlparse
from conda.utils import try_write


log = logging.getLogger(__name__)


default_python = '%d.%d' % sys.version_info[:2]

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

#################################################################
# Also update the example condarc file when you add a key here! #
#################################################################

rc_list_keys = [
    'channels',
    'disallow',
    'create_default_packages',
    'track_features',
    'envs_dirs'
    ]

DEFAULT_CHANNEL_ALIAS = 'https://conda.binstar.org/'

rc_bool_keys = [
    'always_yes',
    'allow_softlinks',
    'changeps1',
    'use_pip',
    'binstar_upload',
    'binstar_personal',
    'show_channel_urls',
    'allow_other_channels',
    ]

# Not supported by conda config yet
rc_other = [
    'proxy_servers',
    'root_dir',
    'channel_alias',
    ]

user_rc_path = abspath(expanduser('~/.condarc'))
sys_rc_path = join(sys.prefix, '.condarc')
def get_rc_path():
    path = os.getenv('CONDARC')
    if path == ' ':
        return None
    if path:
        return path
    for path in user_rc_path, sys_rc_path:
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
                 'config file: %s)' % path)

    return yaml.load(open(path)) or {}

rc = load_condarc(rc_path)

# ----- local directories -----

# root_dir should only be used for testing, which is why don't mention it in
# the documentation, to avoid confusion (it can really mess up a lot of
# things)
root_dir = abspath(expanduser(os.getenv('CONDA_ROOT',
                                        rc.get('root_dir', sys.prefix))))
root_writable = try_write(root_dir)
root_env_name = 'root'

def _default_envs_dirs():
    lst = [join(root_dir, 'envs')]
    if not root_writable:
        lst.insert(0, '~/envs')
    return lst

def _pathsep_env(name):
    x = os.getenv(name)
    if x is None:
        return []
    res = []
    for path in x.split(os.pathsep):
        if path == 'DEFAULTS':
            for p in rc.get('envs_dirs') or _default_envs_dirs():
                res.append(p)
        else:
            res.append(path)
    return res

envs_dirs = [abspath(expanduser(path)) for path in (
        _pathsep_env('CONDA_ENVS_PATH') or
        rc.get('envs_dirs') or
        _default_envs_dirs()
        )]

def pkgs_dir_from_envs_dir(envs_dir):
    if abspath(envs_dir) == abspath(join(root_dir, 'envs')):
        return join(root_dir, 'pkgs')
    else:
        return join(envs_dir, '.pkgs')

pkgs_dirs = [pkgs_dir_from_envs_dir(envs_dir) for envs_dir in envs_dirs]

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

def is_url(url):
    return urlparse.urlparse(url).scheme != ""

def normalize_urls(urls, platform=None):
    platform = platform or subdir
    newurls = []
    for url in urls:
        if url == "defaults":
            newurls.extend(normalize_urls(get_default_urls(),
                                          platform=platform))
        elif url == "system":
            if not rc_path:
                newurls.extend(normalize_urls(get_default_urls(),
                                              platform=platform))
            else:
                newurls.extend(normalize_urls(get_rc_urls(),
                                              platform=platform))
        elif not is_url(url):
            moreurls = normalize_urls([rc.get('channel_alias',
                DEFAULT_CHANNEL_ALIAS)+url], platform=platform)
            newurls.extend(moreurls)
        else:
            newurls.append('%s/%s/' % (url.rstrip('/'), platform))
    return newurls

def get_channel_urls(platform=None):
    if os.getenv('CIO_TEST'):
        base_urls = ['http://filer/pkgs/pro',
                     'http://filer/pkgs/free']
        if os.getenv('CIO_TEST') == '2':
            base_urls.insert(0, 'http://filer/test-pkgs')

    elif 'channels' not in rc:
        base_urls = get_default_urls()

    else:
        base_urls = get_rc_urls()

    return normalize_urls(base_urls, platform=platform)

def canonical_channel_name(channel):
    if channel is None:
        return '<unknown>'
    channel_alias = rc.get('channel_alias', DEFAULT_CHANNEL_ALIAS)
    if channel.startswith(channel_alias):
        return channel.split(channel_alias, 1)[1].split('/')[0]
    elif any(channel.startswith(i) for i in get_default_urls()):
        return 'defaults'
    elif channel.startswith('http://filer/'):
        return 'filer'
    else:
        return channel

# ----- allowed channels -----

def get_allowed_channels():
    if not isfile(sys_rc_path):
        return None
    sys_rc = load_condarc(sys_rc_path)
    if sys_rc.get('allow_other_channels', True):
        return None
    if 'channels' in sys_rc:
        base_urls = sys_rc['channels']
    else:
        base_urls = get_default_urls()
    return normalize_urls(base_urls)

allowed_channels = get_allowed_channels()

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

always_yes = bool(rc.get('always_yes', False))
changeps1 = bool(rc.get('changeps1', True))
use_pip = bool(rc.get('use_pip', True))
binstar_upload = rc.get('binstar_upload', None) # None means ask
binstar_personal = bool(rc.get('binstar_personal', True))
allow_softlinks = bool(rc.get('allow_softlinks', True))
self_update = bool(rc.get('self_update', True))
# show channel URLs when displaying what is going to be downloaded
show_channel_urls = bool(rc.get('show_channel_urls', False))
# set packages disallowed to be installed
disallow = set(rc.get('disallow', []))
# packages which are added to a newly created environment by default
create_default_packages = list(rc.get('create_default_packages', []))
try:
    track_features = set(rc['track_features'].split())
except KeyError:
    track_features = None
