# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import os
import sys
from conda._vendor.auxlib.path import expand
from itertools import chain
from logging import getLogger
from os.path import abspath, basename, dirname, expanduser, isdir, join
from platform import machine

from .constants import DEFAULT_CHANNELS, DEFAULT_CHANNEL_ALIAS, ROOT_ENV_NAME, SEARCH_PATH, conda
from .._vendor.auxlib.compat import NoneType, string_types
from .._vendor.auxlib.ish import dals
from .._vendor.toolz.itertoolz import concatv
from ..common.configuration import (Configuration, MapParameter, PrimitiveParameter,
                                    SequenceParameter)
from ..common.url import urlparse
from ..exceptions import CondaEnvironmentNotFoundError, CondaValueError

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


class Context(Configuration):

    arch_name = property(lambda self: arch_name)
    bits = property(lambda self: bits)
    default_python = property(lambda self: default_python)
    platform = property(lambda self: platform)
    subdir = property(lambda self: subdir)

    add_anaconda_token = PrimitiveParameter(True, aliases=('add_binstar_token',))
    add_pip_as_python_dependency = PrimitiveParameter(True)
    allow_softlinks = PrimitiveParameter(True)
    auto_update_conda = PrimitiveParameter(True, aliases=('self_update',))
    changeps1 = PrimitiveParameter(True)
    create_default_packages = SequenceParameter(string_types)
    disallow = SequenceParameter(string_types)
    ssl_verify = PrimitiveParameter(True, parameter_type=string_types + (bool,))
    track_features = SequenceParameter(string_types)
    use_pip = PrimitiveParameter(True)
    proxy_servers = MapParameter(string_types)
    _root_dir = PrimitiveParameter(sys.prefix, aliases=('root_dir',))

    # channels
    channel_alias = PrimitiveParameter(DEFAULT_CHANNEL_ALIAS)
    channels = SequenceParameter(string_types, default=('defaults',))
    default_channels = SequenceParameter(string_types, DEFAULT_CHANNELS)

    # command line
    always_copy = PrimitiveParameter(False, aliases=('copy',))
    always_yes = PrimitiveParameter(False, aliases=('yes',))
    channel_priority = PrimitiveParameter(True)
    debug = PrimitiveParameter(False)
    json = PrimitiveParameter(False)
    offline = PrimitiveParameter(False)
    quiet = PrimitiveParameter(False)
    shortcuts = PrimitiveParameter(True)
    show_channel_urls = PrimitiveParameter(None, parameter_type=(bool, NoneType))
    update_dependencies = PrimitiveParameter(True, aliases=('update_deps',))
    verbosity = PrimitiveParameter(0, aliases=('verbose',), parameter_type=int)

    # conda_build
    bld_path = PrimitiveParameter('')
    binstar_upload = PrimitiveParameter(None, aliases=('anaconda_upload',),
                                        parameter_type=(bool, NoneType))

    @property
    def local_build_root(self):
        if self.bld_path:
            return expand(self.bld_path)
        elif self.root_writable:
            return join(self.root_dir, 'conda-bld')
        else:
            return expand('~/conda-bld')

    @property
    def force_32bit(self):
        return False

    @property
    def root_dir(self):
        # root_dir is an alias for root_prefix, we prefer the name "root_prefix"
        # because it is more consistent with other names
        return abspath(expanduser(self._root_dir))

    @property
    def root_writable(self):
        from conda.common.disk import try_write
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

    @property
    def prefix(self):
        return get_prefix(self, self._argparse_args, False)

    @property
    def prefix_w_legacy_search(self):
        return get_prefix(self, self._argparse_args, True)

    @property
    def clone_src(self):
        assert self._argparse_args.clone is not None
        return locate_prefix_by_name(self, self._argparse_args.clone)

    @property
    def conda_in_root(self):
        return not conda_in_private_env()

    @property
    def conda_private(self):
        return conda_in_private_env()

    @property
    def root_prefix(self):
        return abspath(join(sys.prefix, '..', '..')) if conda_in_private_env() else sys.prefix

    @property
    def conda_prefix(self):
        return sys.prefix

    @property
    def binstar_hosts(self):
        return (urlparse(self.channel_alias).hostname,
                'anaconda.org',
                'binstar.org')


def conda_in_private_env():
    # conda is located in its own private environment named '_conda'
    return basename(sys.prefix) == '_conda' and basename(dirname(sys.prefix)) == 'envs'

context = Context(SEARCH_PATH, conda, None)


def reset_context(search_path=SEARCH_PATH, argparse_args=None):
    context.__init__(search_path, conda, argparse_args)
    from ..models.channel import Channel
    Channel._reset_state()
    return context


def pkgs_dir_from_envs_dir(envs_dir):
    if abspath(envs_dir) == abspath(join(context.root_dir, 'envs')):
        return join(context.root_dir, 'pkgs32' if context.force_32bit else 'pkgs')
    else:
        return join(envs_dir, '.pkgs')


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


def get_prefix(ctx, args, search=True):
    """Get the prefix to operate in

    Args:
        ctx: the context of conda
        args: the argparse args from the command line
        search: whether search for prefix

    Returns: the prefix
    Raises: CondaEnvironmentNotFoundError if the prefix is invalid
    """
    if args.name:
        if '/' in args.name:
            raise CondaValueError("'/' not allowed in environment name: %s" %
                                  args.name, getattr(args, 'json', False))
        if args.name == ROOT_ENV_NAME:
            return ctx.root_dir
        if search:
            return locate_prefix_by_name(ctx, args.name)
        else:
            return join(ctx.envs_dirs[0], args.name)
    elif args.prefix:
        return abspath(expanduser(args.prefix))
    else:
        return ctx.default_prefix


def locate_prefix_by_name(ctx, name):
    """ Find the location of a prefix given a conda env name.

    Args:
        ctx (Context): the context object
        name (str): the name of prefix to find

    Returns:
        str: the location of the prefix found, or CondaValueError will raise if not found

    Raises:
        CondaValueError: when no prefix is found
    """
    if name == ROOT_ENV_NAME:
        return ctx.root_dir

    # look for a directory named `name` in all envs_dirs AND in CWD
    for envs_dir in chain(ctx.envs_dirs + (os.getcwd(),)):
        prefix = join(envs_dir, name)
        if isdir(prefix):
            return prefix

    raise CondaEnvironmentNotFoundError(name)


def check_write(command, prefix, json=False):
    if inroot_notwritable(prefix):
        from conda.cli.help import root_read_only
        root_read_only(command, prefix, json=json)


def inroot_notwritable(prefix):
    """
    return True if the prefix is under root and root is not writeable
    """
    return (abspath(prefix).startswith(context.root_dir) and
            not context.root_writable)
