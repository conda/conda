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
import re

from conda.compat import urlparse
from conda.utils import try_write, memoized


log = logging.getLogger(__name__)
stderrlog = logging.getLogger('stderrlog')

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

ADD_BINSTAR_TOKEN = True

rc_bool_keys = [
    'add_binstar_token',
    'always_yes',
    'allow_softlinks',
    'changeps1',
    'use_pip',
    'offline',
    'binstar_upload',
    'binstar_personal',
    'show_channel_urls',
    'allow_other_channels',
    'ssl_verify',
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
    if not path or not isfile(path):
        return {}
    try:
        import yaml
    except ImportError:
        sys.exit('Error: could not import yaml (required to read .condarc '
                 'config file: %s)' % path)
    return yaml.load(open(path)) or {}

rc = load_condarc(rc_path)
sys_rc = load_condarc(sys_rc_path) if isfile(sys_rc_path) else {}

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
        # ~/envs for backwards compatibility
        lst = ['~/.conda/envs', '~/envs'] + lst
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
    if isfile(sys_rc_path):
        sys_rc = load_condarc(sys_rc_path)
        if 'default_channels' in sys_rc:
            return sys_rc['default_channels']

    return ['https://repo.continuum.io/pkgs/free',
            'https://repo.continuum.io/pkgs/pro']

def get_rc_urls():
    if rc.get('channels') is None:
        return []
    if 'system' in rc['channels']:
        raise RuntimeError("system cannot be used in .condarc")
    return rc['channels']

def is_url(url):
    return urlparse.urlparse(url).scheme != ""

@memoized
def binstar_channel_alias(channel_alias):
    if rc.get('add_binstar_token', ADD_BINSTAR_TOKEN):
        try:
            from binstar_client.utils import get_binstar
            bs = get_binstar()
            channel_alias = bs.domain.replace("api", "conda")
            if not channel_alias.endswith('/'):
                channel_alias += '/'
            if bs.token:
                channel_alias += 't/%s/' % bs.token
        except ImportError:
            log.debug("Could not import binstar")
            pass
        except Exception as e:
            stderrlog.info("Warning: could not import binstar_client (%s)" %
                e)
    return channel_alias

channel_alias = rc.get('channel_alias', DEFAULT_CHANNEL_ALIAS)
if not sys_rc.get('allow_other_channels', True) and 'channel_alias' in sys_rc:
    channel_alias = sys_rc['channel_alias']

BINSTAR_TOKEN_PAT = re.compile(r'((:?%s|binstar\.org)/?)(t/[0-9a-zA-Z\-<>]{4,})/' %
    (re.escape(channel_alias)))

def hide_binstar_tokens(url):
    return BINSTAR_TOKEN_PAT.sub(r'\1t/<TOKEN>/', url)

def remove_binstar_tokens(url):
    return BINSTAR_TOKEN_PAT.sub(r'\1', url)

def normalize_urls(urls, platform=None):
    channel_alias = binstar_channel_alias(rc.get('channel_alias',
        DEFAULT_CHANNEL_ALIAS))

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
            moreurls = normalize_urls([channel_alias+url], platform=platform)
            newurls.extend(moreurls)
        else:
            newurls.append('%s/%s/' % (url.rstrip('/'), platform))
            newurls.append('%s/noarch/' % url.rstrip('/'))
    return newurls

offline = bool(rc.get('offline', False))

def get_channel_urls(platform=None):
    if os.getenv('CIO_TEST'):
        base_urls = ['http://filer/pkgs/pro',
                     'http://filer/pkgs/free']
        if os.getenv('CIO_TEST') == '2':
            base_urls.insert(0, 'http://filer/test-pkgs')
        return normalize_urls(base_urls, platform=platform)

    if 'channels' not in rc:
        base_urls = get_default_urls()

    else:
        base_urls = get_rc_urls()

    res = normalize_urls(base_urls, platform=platform)
    if offline:
        res = [url for url in res if url.startswith('file:')]
    return res

def canonical_channel_name(channel, hide=True):
    if channel is None:
        return '<unknown>'
    channel = remove_binstar_tokens(channel)
    if channel.startswith(channel_alias):
        end = channel.split(channel_alias, 1)[1]
        url = end.split('/')[0]
        if url == 't' and len(end.split('/')) >= 3:
            url = end.split('/')[2]
        if hide:
            url = hide_binstar_tokens(url)
        return url
    elif any(channel.startswith(i) for i in get_default_urls()):
        return 'defaults'
    elif channel.startswith('http://filer/'):
        return 'filer'
    else:
        if hide:
            return hide_binstar_tokens(channel)
        return channel

# ----- allowed channels -----

def get_allowed_channels():
    if not isfile(sys_rc_path):
        return None
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
    if res is None:
        import requests
        return requests.utils.getproxies()
    if isinstance(res, dict):
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
ssl_verify = bool(rc.get('ssl_verify', True))
try:
    track_features = set(rc['track_features'].split())
except KeyError:
    track_features = None
