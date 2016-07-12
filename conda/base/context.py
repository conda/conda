# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import os
import re
from collections import namedtuple
from logging import getLogger

import sys
from platform import machine

from .constants import SEARCH_PATH, DEFAULT_CHANNEL_ALIAS
from .._vendor.auxlib.compat import string_types
from .._vendor.auxlib.ish import dals
from ..common.configuration import (Configuration as AppConfiguration, PrimitiveParameter,
                                    SequenceParameter, MapParameter)

log = getLogger(__name__)



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


defaults_ = [
    'https://repo.continuum.io/pkgs/free',
    'https://repo.continuum.io/pkgs/pro',
]
if platform == "win":
    defaults_.append('https://repo.continuum.io/pkgs/msys2')







class Binstar(object):

    # binstar_regex = r'((:?binstar\.org|anaconda\.org)/?)(t/[0-9a-zA-Z\-<>]{4,})/'
    # BINSTAR_TOKEN_PAT = re.compile(binstar_regex)
    # channel_alias = rc.get('channel_alias', None)
    # if not sys_rc.get('allow_other_channels', True) and 'channel_alias' in sys_rc:
    #     channel_alias = sys_rc['channel_alias']
    # if channel_alias is not None:
    #     channel_alias = remove_binstar_tokens(channel_alias.rstrip('/') + '/')
    # channel_alias_tok = binstar_client = binstar_domain = binstar_domain_tok = None

    def __init__(self, quiet=False):
        # global binstar_client, binstar_domain, binstar_domain_tok
        # global binstar_regex, BINSTAR_TOKEN_PAT
        if getattr(self, 'binstar_domain', None) is not None:
            return
        elif getattr(self, 'binstar_client', None) is None:
            try:
                from binstar_client.utils import get_binstar
                # Turn off output in offline mode so people don't think we're going online
                args = namedtuple('args', 'log_level')(0) if quiet or offline else None
                self.binstar_client = get_binstar(args)
            except ImportError:
                log.debug("Could not import binstar")
                self.binstar_client = ()
            except Exception as e:
                stderrlog.info("Warning: could not import binstar_client (%s)" % e)
        if self.binstar_client == ():
            self.binstar_domain = DEFAULT_CHANNEL_ALIAS
            self.binstar_domain_tok = None
        else:
            self.binstar_domain = self.binstar_client.domain.replace("api", "conda").rstrip('/') + '/'
            if self.binstar_client.token:
                self.binstar_domain_tok = self.binstar_domain + 't/%s/' % (self.binstar_client.token,)
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
    binstar_upload = PrimitiveParameter(None, aliases=('anaconda_upload', ))
    allow_softlinks = PrimitiveParameter(True)
    self_update = PrimitiveParameter(True)
    show_channel_urls = PrimitiveParameter(None)
    update_dependencies = PrimitiveParameter(True)
    channel_priority = PrimitiveParameter(True)
    ssl_verify = PrimitiveParameter(True)
    track_features = SequenceParameter(string_types)
    disallow = SequenceParameter(string_types)
    create_default_packages = SequenceParameter(string_types)
    # envs_dirs = SequenceParameter(string_types)

    channels = SequenceParameter(string_types)
    default_channels = SequenceParameter(string_types)

    proxy_servers = MapParameter(string_types)










context = Context.from_search_path(SEARCH_PATH)


# def reset_context(search_path):
#     global context
#     context = Context.from_search_path(search_path)


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
