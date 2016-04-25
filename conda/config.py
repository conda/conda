# (c) 2012-2015 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import logging
import os
import re
import sys
from collections import OrderedDict
from os.path import abspath, expanduser, isfile, isdir, join
from platform import machine

from conda.compat import urlparse
from conda.utils import try_write, memoized, yaml_load

log = logging.getLogger(__name__)
stderrlog = logging.getLogger('stderrlog')

default_python = '%d.%d' % sys.version_info[:2]
# CONDA_FORCE_32BIT should only be used when running conda-build (in order
# to build 32-bit packages on a 64-bit system).  We don't want to mention it
# in the documentation, because it can mess up a lot of things.
force_32bit = bool(int(os.getenv('CONDA_FORCE_32BIT', 0)))

# ----- operating system and architecture -----

_sys_map = {'linux2': 'linux', 'linux': 'linux',
            'darwin': 'osx', 'win32': 'win', 'openbsd5': 'openbsd'}
non_x86_linux_machines = {'armv6l', 'armv7l', 'ppc64le'}
platform = _sys_map.get(sys.platform, 'unknown')
bits = 8 * tuple.__itemsize__
if force_32bit:
    bits = 32

if platform == 'linux' and machine() in non_x86_linux_machines:
    arch_name = machine()
    subdir = 'linux-%s' % arch_name
else:
    arch_name = {64: 'x86_64', 32: 'x86'}[bits]
    subdir = '%s-%d' % (platform, bits)

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
    'envs_dirs',
    'default_channels',
]

DEFAULT_CHANNEL_ALIAS = 'https://conda.anaconda.org/'

ADD_BINSTAR_TOKEN = True

rc_bool_keys = [
    'add_binstar_token',
    'add_anaconda_token',
    'add_pip_as_python_dependency',
    'always_yes',
    'always_copy',
    'allow_softlinks',
    'changeps1',
    'use_pip',
    'offline',
    'binstar_upload',
    'anaconda_upload',
    'show_channel_urls',
    'allow_other_channels',
    'update_dependencies',
    'channel_priority',
]

rc_string_keys = [
    'ssl_verify',
    'channel_alias',
    'root_dir',
]

# Not supported by conda config yet
rc_other = [
    'proxy_servers',
]

user_rc_path = abspath(expanduser('~/.condarc'))
sys_rc_path = join(sys.prefix, '.condarc')
local_channel = []

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
        print("no path!")
        return {}
    with open(path) as f:
        return yaml_load(f) or {}

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
        return join(root_dir, 'pkgs32' if force_32bit else 'pkgs')
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

# Note, get_*_urls() return unnormalized urls.

def get_local_urls(clear_cache=True):
    # remove the cache such that a refetch is made,
    # this is necessary because we add the local build repo URL
    if clear_cache:
        from conda.fetch import fetch_index
        fetch_index.cache = {}
    if local_channel:
        return local_channel
    from os.path import exists
    from conda.utils import url_path
    try:
        from conda_build.config import croot
        if exists(croot):
            local_channel.append(url_path(croot))
    except ImportError:
        pass
    return local_channel

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
    if rc.get('add_anaconda_token',
              rc.get('add_binstar_token', ADD_BINSTAR_TOKEN)):
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
            stderrlog.info("Warning: could not import binstar_client (%s)" % e)
    return channel_alias

channel_alias = rc.get('channel_alias', DEFAULT_CHANNEL_ALIAS)
if not sys_rc.get('allow_other_channels', True) and 'channel_alias' in sys_rc:
    channel_alias = sys_rc['channel_alias']

_binstar = r'((:?%s|binstar\.org|anaconda\.org)/?)(t/[0-9a-zA-Z\-<>]{4,})/'
BINSTAR_TOKEN_PAT = re.compile(_binstar % re.escape(channel_alias))

def hide_binstar_tokens(url):
    return BINSTAR_TOKEN_PAT.sub(r'\1t/<TOKEN>/', url)

def remove_binstar_tokens(url):
    return BINSTAR_TOKEN_PAT.sub(r'\1', url)

channel_alias = remove_binstar_tokens(channel_alias.rstrip('/') + '/')

def normalize_urls(urls, platform=None, offline_only=False):
    platform = platform or subdir
    defaults = tuple(x.rstrip('/') + '/' for x in get_default_urls())
    alias = binstar_channel_alias(channel_alias)

    def normalize_(url):
        url = url.rstrip('/')
        if is_url(url):
            url_s = canonical_channel_name(url, True)
        else:
            url_s = url
            url = alias + url
        return url_s, url
    newurls = OrderedDict()
    priority = 0
    while urls:
        url = urls[0]
        urls = urls[1:]
        if url == "system" and rc_path:
            urls = get_rc_urls() + urls
            continue
        elif url in ("defaults", "system"):
            t_urls = defaults
        elif url == "local":
            t_urls = get_local_urls()
        else:
            t_urls = [url]
        priority += 1
        for url0 in t_urls:
            url_s, url0 = normalize_(url0)
            if offline_only and not url0.startswith('file:'):
                continue
            for plat in (platform, 'noarch'):
                newurls.setdefault('%s/%s/' % (url0, plat), (url_s, priority))
    return newurls

offline = bool(rc.get('offline', False))

def get_channel_urls(platform=None, offline=False):
    if os.getenv('CIO_TEST'):
        import cio_test
        base_urls = cio_test.base_urls
    elif 'channels' in rc:
        base_urls = ['system']
    else:
        base_urls = ['defaults']
    res = normalize_urls(base_urls, platform, offline)
    return res

def canonical_channel_name(channel, hide=True, no_unknown=False):
    if channel is None:
        return 'defaults' if no_unknown else '<unknown>'
    channel = remove_binstar_tokens(channel)
    if any(channel.startswith(i) for i in get_default_urls()):
        return 'defaults'
    elif any(channel.startswith(i) for i in get_local_urls(clear_cache=False)):
        return 'local'
    elif channel.startswith('http://filer/'):
        return 'filer'
    elif channel.startswith(channel_alias):
        return channel.split(channel_alias, 1)[1]
    else:
        return channel

def url_channel(url):
    if url is None:
        return None, '<unknown>'
    channel = url.rsplit('/', 2)[0]
    schannel = canonical_channel_name(channel)
    return channel, schannel

# ----- allowed channels -----

def get_allowed_channels():
    if not isfile(sys_rc_path):
        return None
    if sys_rc.get('allow_other_channels', True):
        return None
    if 'channels' in sys_rc:
        base_urls = ['system']
    else:
        base_urls = ['default']
    return normalize_urls(base_urls)

allowed_channels = get_allowed_channels()

# ----- proxy -----

def get_proxy_servers():
    res = rc.get('proxy_servers') or {}
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

add_pip_as_python_dependency = bool(rc.get('add_pip_as_python_dependency', True))
always_yes = bool(rc.get('always_yes', False))
always_copy = bool(rc.get('always_copy', False))
changeps1 = bool(rc.get('changeps1', True))
use_pip = bool(rc.get('use_pip', True))
binstar_upload = rc.get('anaconda_upload',
                        rc.get('binstar_upload', None))  # None means ask
allow_softlinks = bool(rc.get('allow_softlinks', True))
self_update = bool(rc.get('self_update', True))
# show channel URLs when displaying what is going to be downloaded
show_channel_urls = rc.get('show_channel_urls', None)  # None means letting conda decide
# set packages disallowed to be installed
disallow = set(rc.get('disallow', []))
# packages which are added to a newly created environment by default
create_default_packages = list(rc.get('create_default_packages', []))
update_dependencies = bool(rc.get('update_dependencies', True))
channel_priority = bool(rc.get('channel_priority', True))

# ssl_verify can be a boolean value or a filename string
ssl_verify = rc.get('ssl_verify', True)

try:
    track_features = set(rc['track_features'])
except KeyError:
    track_features = None
