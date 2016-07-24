# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import os
import re
import sys
from logging import getLogger, WARN, INFO
from os.path import expanduser, abspath, join, isdir
from platform import machine

from requests.packages.urllib3.util.url import parse_url

from .._vendor.toolz.itertoolz import concatv
from ..common.io import captured, disable_logger
from .constants import SEARCH_PATH, DEFAULT_CHANNEL_ALIAS, DEFAULT_CHANNELS, conda, ROOT_ENV_NAME
from .._vendor.auxlib.compat import string_types, NoneType
from .._vendor.auxlib.ish import dals
from ..common.configuration import (Configuration as AppConfiguration, PrimitiveParameter,
                                    SequenceParameter, MapParameter, load_raw_configs)

log = getLogger(__name__)
stderrlog = getLogger('stderrlog')


default_python = '%d.%d' % sys.version_info[:2]
# CONDA_FORCE_32BIT should only be used when running conda-build (in order
# to build 32-bit packages on a 64-bit system).  We don't want to mention it
# in the documentation, because it can mess up a lot of things.
force_32bit = bool(int(os.getenv('CONDA_FORCE_32BIT', 0)))

# ----- operating system and architecture -----

_sys_map = {
    'linux2': 'linux',
    'linux': 'linux',
    'darwin': 'osx',
    'win32': 'win',
    'openbsd5': 'openbsd',
}
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


class Context(AppConfiguration):

    subdir = property(lambda self: subdir)
    platform = property(lambda self: platform)
    default_python = property(lambda self: default_python)

    add_anaconda_token = PrimitiveParameter(True, aliases=('add_binstar_token',))
    add_pip_as_python_dependency = PrimitiveParameter(True)
    always_yes = PrimitiveParameter(False)
    always_copy = PrimitiveParameter(False)
    changeps1 = PrimitiveParameter(True)
    use_pip = PrimitiveParameter(True)
    shortcuts = PrimitiveParameter(True)
    offline = PrimitiveParameter(False)
    binstar_upload = PrimitiveParameter(None, aliases=('anaconda_upload',))
    allow_softlinks = PrimitiveParameter(True)
    auto_update_conda = PrimitiveParameter(True, aliases=('self_update',))
    show_channel_urls = PrimitiveParameter(None, parameter_type=(bool, NoneType))
    update_dependencies = PrimitiveParameter(True)
    channel_priority = PrimitiveParameter(True)
    ssl_verify = PrimitiveParameter(True, parameter_type=string_types + (bool,))
    track_features = SequenceParameter(string_types)
    disallow = SequenceParameter(string_types)
    create_default_packages = SequenceParameter(string_types)

    channel_alias = PrimitiveParameter(DEFAULT_CHANNEL_ALIAS)
    channels = SequenceParameter(string_types, default=('defaults',))
    default_channels = SequenceParameter(string_types, DEFAULT_CHANNELS)

    proxy_servers = MapParameter(string_types)

    _root_dir = PrimitiveParameter(sys.prefix, aliases=('root_dir',))

    @property
    def force_32bit(self):
        return False

    @property
    def root_dir(self):
        return abspath(expanduser(self._root_dir))

    @property
    def root_writable(self):
        from ..utils import try_write
        return try_write(self.root_dir)

    _envs_dirs = SequenceParameter(string_types, aliases=('envs_dirs',))

    @property
    def envs_dirs(self):
        return tuple(abspath(expanduser(p))
                     for p in concatv(self._envs_dirs,
                                      (join(self.root_dir, 'envs'), )
                                      if self.root_writable
                                      else ('~/.conda/envs', join(self.root_dir, 'envs'))))

    @property
    def pkgs_dirs(self):
        return [pkgs_dir_from_envs_dir(envs_dir) for envs_dir in self.envs_dirs]

    @property
    def default_prefix(self):
        _default_env = os.getenv('CONDA_DEFAULT_ENV')
        if _default_env in (None, ROOT_ENV_NAME):
            return self.root_dir
        elif os.sep in _default_env:
            return abspath(_default_env)
        else:
            for envs_dir in self.envs_dirs:
                default_prefix = join(envs_dir, _default_env)
                if isdir(default_prefix):
                    return default_prefix
        return join(self.envs_dirs[0], _default_env)


context = Context.from_search_path(SEARCH_PATH, conda)


def pkgs_dir_from_envs_dir(envs_dir):
    if abspath(envs_dir) == abspath(join(context.root_dir, 'envs')):
        return join(context.root_dir, 'pkgs32' if context.force_32bit else 'pkgs')
    else:
        return join(envs_dir, '.pkgs')


def reset_context(search_path):
    # TODO: move to test module
    context._load(load_raw_configs(search_path), conda)
    from ..entities.channel import Channel
    Channel._reset_state()
    return context


def get_help_dict():
    # this is a function so that most of the time it's not evaluated and loaded into memory
    return {
        'add_pip_as_python_dependency': dals("""
            """),
        'always_yes': dals("""
            """),
        'always_copy': dals("""
            """),
        'changeps1': dals("""
            """),
        'use_pip': dals("""
            Use pip when listing packages with conda list. Note that this does not affect any
            conda command or functionality other than the output of the command conda list.
            """),
        'binstar_upload': dals("""
            """),
        'allow_softlinks': dals("""
            """),
        'self_update': dals("""
            """),
        'show_channel_urls': dals("""
            # show channel URLs when displaying what is going to be downloaded
            # None means letting conda decide
            """),
        'update_dependencies': dals("""
            """),
        'channel_priority': dals("""
            """),
        'ssl_verify': dals("""
            # ssl_verify can be a boolean value or a filename string
            """),
        'track_features': dals("""
            """),
        'channels': dals("""
            """),
        'disallow': dals("""
            # set packages disallowed to be installed
            """),
        'create_default_packages': dals("""
            # packages which are added to a newly created environment by default
            """),
        'envs_dirs': dals("""
            """),
        'default_channels': dals("""
            """),
        'proxy_servers': dals("""
            """),
    }
