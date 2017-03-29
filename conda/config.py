# (c) 2012-2015 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
from __future__ import print_function, division, absolute_import, unicode_literals

import os
import sys
from os.path import abspath, expanduser, isfile, join

from conda.base.context import context, non_x86_linux_machines
non_x86_linux_machines = non_x86_linux_machines


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
    'pkgs_dirs',
    'default_channels',
    'pinned_packages',
]

rc_bool_keys = [
    'add_binstar_token',
    'add_anaconda_token',
    'add_pip_as_python_dependency',
    'always_yes',
    'always_copy',
    'allow_softlinks',
    'always_softlink',
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
    'channel_alias',
    'client_ssl_cert',
    'client_ssl_cert_key',
    'default_python',
]

# Not supported by conda config yet
rc_other = [
    'proxy_servers',
]

root_dir = context.root_prefix
root_writable = context.root_writable

user_rc_path = abspath(expanduser('~/.condarc'))
sys_rc_path = join(sys.prefix, '.condarc')


get_rc_urls = lambda: context.channels


def get_local_urls():
    from conda.models.channel import get_conda_build_local_url
    return get_conda_build_local_url() or []


class RC(object):

    def get(self, key, default=None):
        key = key.replace('-', '_')
        return getattr(context, key, default)


rc = RC()
envs_dirs = context.envs_dirs


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

pkgs_dirs = list(context.pkgs_dirs)
default_prefix = context.default_prefix
subdir = context.subdir
arch_name = context.arch_name
bits = context.bits
platform = context.platform

# put back because of conda build
default_python = context.default_python
binstar_upload = context.anaconda_upload
