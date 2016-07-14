# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import os
import re
import sys
from logging import getLogger, WARN, INFO
from os.path import expanduser, abspath, join, isdir
from platform import machine

from conda._vendor.toolz.itertoolz import concatv
from .constants import SEARCH_PATH, DEFAULT_CHANNEL_ALIAS, DEFAULT_CHANNELS, conda, ROOT_ENV_NAME
from .._vendor.auxlib.compat import string_types
from .._vendor.auxlib.ish import dals
from ..common.configuration import (Configuration as AppConfiguration, PrimitiveParameter,
                                    SequenceParameter, MapParameter)

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



class Binstar(object):

    # binstar_regex = r'((:?binstar\.org|anaconda\.org)/?)(t/[0-9a-zA-Z\-<>]{4,})/'
    # BINSTAR_TOKEN_PAT = re.compile(binstar_regex)
    # channel_alias = rc.get('channel_alias', None)
    # if not sys_rc.get('allow_other_channels', True) and 'channel_alias' in sys_rc:
    #     channel_alias = sys_rc['channel_alias']
    # if channel_alias is not None:
    #     channel_alias = remove_binstar_tokens(channel_alias.rstrip('/') + '/')
    # channel_alias_tok = binstar_client = binstar_domain = binstar_domain_tok = None

    def __init__(self, url=DEFAULT_CHANNEL_ALIAS, token=None, quiet=True):
        try:
            from binstar_client.utils import get_server_api
            self.binstar_client = get_server_api(token=token, site=url,
                                                 log_level=WARN if quiet else INFO)
        except ImportError:
            log.debug("Could not import binstar")
            self.binstar_client = ()
        except Exception as e:
            stderrlog.info("Warning: could not import binstar_client (%s)" % e)
            self.binstar_client = ()
        if self.binstar_client:
            self.binstar_domain = self.binstar_client.domain.replace("api", "conda").rstrip('/') + '/'
            if self.binstar_client.token:
                self.binstar_domain_tok = self.binstar_domain + 't/%s/' % (self.binstar_client.token,)
        else:
            self.binstar_domain = DEFAULT_CHANNEL_ALIAS
            self.binstar_domain_tok = None
        self.binstar_regex = (r'((:?%s|binstar\.org|anaconda\.org)/?)(t/[0-9a-zA-Z\-<>]{4,})/' %
                              re.escape(self.binstar_domain[:-1]))
        self.BINSTAR_TOKEN_PAT = re.compile(self.binstar_regex)

        # from channel_prefix
        self.channel_alias = self.binstar_domain
        self.channel_alias_tok = self.binstar_domain_tok
        if self.channel_alias is None:
            self.channel_alias = DEFAULT_CHANNEL_ALIAS
        if self.channel_alias_tok is None:
            self.channel_alias_tok = self.channel_alias

    def channel_prefix(self, token=False):
        # global channel_alias, channel_alias_tok
        return self.channel_alias_tok if token else self.channel_alias

    def add_binstar_tokens(self, url):
        if self.binstar_domain_tok and url.startswith(self.binstar_domain):
            url2 = self.BINSTAR_TOKEN_PAT.sub(r'\1', url)
            if url2 == url:
                return self.binstar_domain_tok + url.split(self.binstar_domain, 1)[1]
        return url

    def hide_binstar_tokens(self, url):
        return self.BINSTAR_TOKEN_PAT.sub(r'\1t/<TOKEN>/', url)

    def remove_binstar_tokens(self, url):
        return self.BINSTAR_TOKEN_PAT.sub(r'\1', url)

binstar = Binstar()


class Context(AppConfiguration):

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
    show_channel_urls = PrimitiveParameter(None)
    update_dependencies = PrimitiveParameter(True)
    channel_priority = PrimitiveParameter(True)
    ssl_verify = PrimitiveParameter(True, parameter_type=string_types + (bool,))
    track_features = SequenceParameter(string_types)
    disallow = SequenceParameter(string_types)
    create_default_packages = SequenceParameter(string_types)

    channel_alias = PrimitiveParameter(DEFAULT_CHANNEL_ALIAS)
    channels = SequenceParameter(string_types)
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
        def pkgs_dir_from_envs_dir(envs_dir):
            if abspath(envs_dir) == abspath(join(self.root_dir, 'envs')):
                return join(self.root_dir, 'pkgs32' if context.force_32bit else 'pkgs')
            else:
                return join(envs_dir, '.pkgs')
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

    @property
    def subdir(self):
        return subdir

    @property
    def platform(self):
        return platform

    @property
    def default_python(self):
        return default_python



context = Context.from_search_path(SEARCH_PATH, conda)


def reset_context(search_path):
    global context
    context = Context.from_search_path(search_path, conda)


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


if __name__ == "__main__":
    import pdb; pdb.set_trace()
