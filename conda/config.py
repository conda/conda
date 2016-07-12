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
from collections import OrderedDict, namedtuple
from os.path import abspath, basename, dirname, expanduser, isfile, isdir, join
from platform import machine

from .compat import urlparse, string_types
from .utils import try_write, yaml_load
from .exceptions import ProxyError, CondaRuntimeError

from conda.base.context import context, reset_context


log = logging.getLogger(__name__)
stderrlog = logging.getLogger('stderrlog')

output_json = False
debug_on = False


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
    'auto_update_conda',
    'changeps1',
    'use_pip',
    'offline',
    'binstar_upload',
    'anaconda_upload',
    'show_channel_urls',
    'allow_other_channels',
    'update_dependencies',
    'channel_priority',
    'shortcuts',
]

rc_string_keys = [
    'ssl_verify',
    'channel_alias',
]

# Not supported by conda config yet
rc_other = [
    'proxy_servers',
]

if basename(sys.prefix) == '_conda' and basename(dirname(sys.prefix)) == 'envs':
    # conda is located in it's own private environment named '_conda'
    conda_in_root = False
    conda_private = True
    root_prefix = abspath(join(sys.prefix, '..', '..'))
    conda_prefix = sys.prefix
else:
    # conda is located in the root environment
    conda_in_root = True
    conda_private = False
    root_prefix = conda_prefix = abspath(sys.prefix)

# root_dir is an alias for root_prefix, we prefer the name "root_prefix"
# because it is more consistent with other names
root_dir = root_prefix

user_rc_path = abspath(expanduser('~/.condarc'))
sys_rc_path = join(sys.prefix, '.condarc')
root_dir = root_writable = None
offline = False
add_anaconda_token = ADD_BINSTAR_TOKEN
rc = {}

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

def load_condarc_(path):
    if not path or not isfile(path):
        return {}
    with open(path) as f:
        reset_context(path,)
        return yaml_load(f) or {}

sys_rc = load_condarc_(sys_rc_path) if isfile(sys_rc_path) else {}

# ----- local directories -----

# root_dir should only be used for testing, which is why don't mention it in
# the documentation, to avoid confusion (it can really mess up a lot of
# things)
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

def pkgs_dir_from_envs_dir(envs_dir):
    if abspath(envs_dir) == abspath(join(root_dir, 'envs')):
        return join(root_dir, 'pkgs32' if force_32bit else 'pkgs')
    else:
        return join(envs_dir, '.pkgs')


def is_url(url):
    if url:
        p = urlparse.urlparse(url)
        return p.netloc != "" or p.scheme == "file"




def set_offline():
    global offline
    offline = True

def is_offline():
    return offline

def offline_keep(url):
    return not offline or not is_url(url) or url.startswith('file:/')




# ----- proxy -----

def get_proxy_servers():
    res = rc.get('proxy_servers') or {}
    if isinstance(res, dict):
        return res
    raise ProxyError('proxy_servers setting not a mapping')


def load_condarc(path=None):
    global rc
    if path is not None:
        rc = load_condarc_(path)

    root_writable = try_write(root_dir)

    globals().update(locals())

    envs_dirs = [abspath(expanduser(p)) for p in (
            _pathsep_env('CONDA_ENVS_PATH') or
            rc.get('envs_dirs') or
            _default_envs_dirs()
            )]

    pkgs_dirs = [pkgs_dir_from_envs_dir(envs_dir) for envs_dir in envs_dirs]

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

    # ----- foreign -----

    try:
        with open(join(root_dir, 'conda-meta', 'foreign')) as fi:
            foreign = fi.read().split()
    except IOError:
        foreign = [] if isdir(join(root_dir, 'conda-meta')) else ['python']

    offline = bool(rc.get('offline', False))
    add_anaconda_token = rc.get('add_anaconda_token',
                                rc.get('add_binstar_token', ADD_BINSTAR_TOKEN))

    add_pip_as_python_dependency = bool(rc.get('add_pip_as_python_dependency', True))
    always_yes = context.always_yes
    always_copy = bool(rc.get('always_copy', False))
    changeps1 = bool(rc.get('changeps1', True))
    use_pip = bool(rc.get('use_pip', True))
    binstar_upload = rc.get('anaconda_upload',
                            rc.get('binstar_upload', None))  # None means ask
    allow_softlinks = bool(rc.get('allow_softlinks', True))
    auto_update_conda = bool(rc.get('auto_update_conda',
                                    rc.get('self_update',
                                           sys_rc.get('auto_update_conda', True))))
    # show channel URLs when displaying what is going to be downloaded
    show_channel_urls = rc.get('show_channel_urls', None)  # None means letting conda decide
    # set packages disallowed to be installed
    disallow = set(rc.get('disallow', []))
    # packages which are added to a newly created environment by default
    create_default_packages = list(rc.get('create_default_packages', []))
    update_dependencies = bool(rc.get('update_dependencies', True))
    channel_priority = bool(rc.get('channel_priority', True))
    shortcuts = bool(rc.get('shortcuts', True))

    # ssl_verify can be a boolean value or a filename string
    ssl_verify = rc.get('ssl_verify', True)

    try:
        track_features = rc.get('track_features', [])
        if isinstance(track_features, string_types):
            track_features = track_features.split()
        track_features = set(track_features)
    except KeyError:
        track_features = None

    globals().update(locals())
    return rc

load_condarc(rc_path)
