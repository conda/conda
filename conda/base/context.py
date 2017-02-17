# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import Sequence
from logging import getLogger
import os
from os.path import (abspath, basename, dirname, expanduser, isdir, isfile, join, normpath,
                     split as path_split)
from platform import machine
import sys

from .constants import (APP_NAME, DEFAULTS_CHANNEL_NAME, DEFAULT_CHANNELS, DEFAULT_CHANNEL_ALIAS,
                        PathConflict, ROOT_ENV_NAME, SEARCH_PATH)
from .. import CondaError
from .._vendor.appdirs import user_data_dir
from .._vendor.auxlib.collection import first
from .._vendor.auxlib.decorators import memoizedproperty
from .._vendor.auxlib.ish import dals
from .._vendor.auxlib.path import expand
from .._vendor.boltons.setutils import IndexedSet
from ..common.compat import NoneType, iteritems, itervalues, odict, on_win, string_types, text_type
from ..common.configuration import (Configuration, LoadError, MapParameter, PrimitiveParameter,
                                    SequenceParameter, ValidationError)
from ..common.disk import conda_bld_ensure_dir
from ..common.url import has_scheme, path_to_url, split_scheme_auth_token
from ..exceptions import CondaEnvironmentNotFoundError, CondaValueError

try:
    from cytoolz.itertoolz import concat, concatv, unique
except ImportError:
    from .._vendor.toolz.itertoolz import concat, concatv, unique

log = getLogger(__name__)

try:
    import cio_test  # NOQA
except ImportError:
    log.info("No cio_test package found.")

_platform_map = {
    'linux2': 'linux',
    'linux': 'linux',
    'darwin': 'osx',
    'win32': 'win',
}
non_x86_linux_machines = {
    'armv6l',
    'armv7l',
    'ppc64le',
}
_arch_names = {
    32: 'x86',
    64: 'x86_64',
}


def channel_alias_validation(value):
    if value and not has_scheme(value):
        return "channel_alias value '%s' must have scheme/protocol." % value
    return True


def ssl_verify_validation(value):
    if isinstance(value, string_types):
        if not isfile(value):
            return ("ssl_verify value '%s' must be a boolean or a path to a "
                    "certificate bundle." % value)
    return True


class Context(Configuration):

    add_pip_as_python_dependency = PrimitiveParameter(True)
    allow_softlinks = PrimitiveParameter(True)
    auto_update_conda = PrimitiveParameter(True, aliases=('self_update',))
    clobber = PrimitiveParameter(False)
    changeps1 = PrimitiveParameter(True)
    concurrent = PrimitiveParameter(False)
    create_default_packages = SequenceParameter(string_types)
    default_python = PrimitiveParameter('%d.%d' % sys.version_info[:2],
                                        parameter_type=string_types + (NoneType,))
    disallow = SequenceParameter(string_types)
    force_32bit = PrimitiveParameter(False)
    path_conflict = PrimitiveParameter(PathConflict.clobber)
    rollback_enabled = PrimitiveParameter(True)
    track_features = SequenceParameter(string_types)
    use_pip = PrimitiveParameter(True)

    _root_dir = PrimitiveParameter("", aliases=('root_dir',))
    _envs_dirs = SequenceParameter(string_types, aliases=('envs_dirs', 'envs_path'),
                                   string_delimiter=os.pathsep)
    _pkgs_dirs = SequenceParameter(string_types, aliases=('pkgs_dirs',))
    _subdir = PrimitiveParameter('', aliases=('subdir',))

    local_repodata_ttl = PrimitiveParameter(True, parameter_type=(bool, int))
    # number of seconds to cache repodata locally
    #   True/1: respect Cache-Control max-age header
    #   False/0: always fetch remote repodata (HTTP 304 responses respected)

    # remote connection details
    ssl_verify = PrimitiveParameter(True, parameter_type=string_types + (bool,),
                                    validation=ssl_verify_validation)
    client_ssl_cert = PrimitiveParameter('', aliases=('client_cert',))
    client_ssl_cert_key = PrimitiveParameter('', aliases=('client_cert_key',))
    proxy_servers = MapParameter(string_types)
    remote_connect_timeout_secs = PrimitiveParameter(9.15)
    remote_read_timeout_secs = PrimitiveParameter(60.)
    remote_max_retries = PrimitiveParameter(3)

    add_anaconda_token = PrimitiveParameter(True, aliases=('add_binstar_token',))
    _channel_alias = PrimitiveParameter(DEFAULT_CHANNEL_ALIAS,
                                        aliases=('channel_alias',),
                                        validation=channel_alias_validation)
    allow_non_channel_urls = PrimitiveParameter(True)

    # channels
    _channels = SequenceParameter(string_types, default=(DEFAULTS_CHANNEL_NAME,),
                                  aliases=('channels', 'channel',))  # channel for args.channel
    _migrated_channel_aliases = SequenceParameter(string_types,
                                                  aliases=('migrated_channel_aliases',))  # TODO: also take a list of strings # NOQA
    _default_channels = SequenceParameter(string_types, DEFAULT_CHANNELS,
                                          aliases=('default_channels',))
    _custom_channels = MapParameter(string_types, aliases=('custom_channels',))
    migrated_custom_channels = MapParameter(string_types)  # TODO: also take a list of strings
    _custom_multichannels = MapParameter(Sequence, aliases=('custom_multichannels',))

    # command line
    always_softlink = PrimitiveParameter(False, aliases=('softlink',))
    always_copy = PrimitiveParameter(False, aliases=('copy',))
    always_yes = PrimitiveParameter(False, aliases=('yes',))
    channel_priority = PrimitiveParameter(True)
    debug = PrimitiveParameter(False)
    force = PrimitiveParameter(False)
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
    _croot = PrimitiveParameter('', aliases=('croot',))
    conda_build = MapParameter(string_types, aliases=('conda-build',))

    def post_build_validation(self):
        errors = []
        if self.client_ssl_cert_key and not self.client_ssl_cert:
            error = ValidationError('client_ssl_cert', self.client_ssl_cert, "<<merged>>",
                                    "'client_ssl_cert' is required when 'client_ssl_cert_key' "
                                    "is defined")
            errors.append(error)
        if self.always_copy and self.always_softlink:
            error = ValidationError('always_copy', self.always_copy, "<<merged>>",
                                    "'always_copy' and 'always_softlink' are mutually exclusive. "
                                    "Only one can be set to 'True'.")
            errors.append(error)
        return errors

    @property
    def conda_build_local_paths(self):
        # does file system reads to make sure paths actually exist
        return tuple(unique(full_path for full_path in (
            expand(d) for d in (
                self._croot,
                self.bld_path,
                self.conda_build.get('root-dir'),
                join(self.root_prefix, 'conda-bld'),
                '~/conda-bld',
            ) if d
        ) if isdir(full_path)))

    @property
    def conda_build_local_urls(self):
        return tuple(path_to_url(p) for p in self.conda_build_local_paths)

    @property
    def croot(self):
        """This is where source caches and work folders live"""
        if self._croot:
            return abspath(expanduser(self._croot))
        elif self.bld_path:
            return abspath(expanduser(self.bld_path))
        elif 'root-dir' in self.conda_build:
            return abspath(expanduser(self.conda_build['root-dir']))
        elif self.root_writable:
            return join(self.root_prefix, 'conda-bld')
        else:
            return expand('~/conda-bld')

    @property
    def src_cache(self):
        path = join(self.croot, 'src_cache')
        conda_bld_ensure_dir(path)
        return path

    @property
    def git_cache(self):
        path = join(self.croot, 'git_cache')
        conda_bld_ensure_dir(path)
        return path

    @property
    def hg_cache(self):
        path = join(self.croot, 'hg_cache')
        conda_bld_ensure_dir(path)
        return path

    @property
    def svn_cache(self):
        path = join(self.croot, 'svn_cache')
        conda_bld_ensure_dir(path)
        return path

    @property
    def arch_name(self):
        m = machine()
        if self.platform == 'linux' and m in non_x86_linux_machines:
            return m
        else:
            return _arch_names[self.bits]

    @property
    def platform(self):
        return _platform_map.get(sys.platform, 'unknown')

    @property
    def subdir(self):
        if self._subdir:
            return self._subdir
        m = machine()
        if m in non_x86_linux_machines:
            return 'linux-%s' % m
        else:
            return '%s-%d' % (self.platform, self.bits)

    @property
    def bits(self):
        if self.force_32bit:
            return 32
        else:
            return 8 * tuple.__itemsize__

    @property
    def local_build_root(self):
        # TODO: import from conda_build, and fall back to something incredibly simple
        if self.bld_path:
            return expand(self.bld_path)
        elif self.root_writable:
            return join(self.conda_prefix, 'conda-bld')
        else:
            return expand('~/conda-bld')

    @property
    def root_dir(self):
        # root_dir is an alias for root_prefix, we prefer the name "root_prefix"
        # because it is more consistent with other names
        return self.root_prefix

    @property
    def root_writable(self):
        from ..gateways.disk.test import prefix_is_writable
        return prefix_is_writable(self.root_prefix)

    @property
    def envs_dirs(self):
        if self.root_writable:
            fixed_dirs = (
                join(self.root_prefix, 'envs'),
                join(self._user_data_dir, 'envs'),
                join('~', '.conda', 'envs'),
            )
        else:
            fixed_dirs = (
                join(self.root_prefix, 'envs'),
                join(self._user_data_dir, 'envs'),
                join('~', '.conda', 'envs'),
            )
        return tuple(IndexedSet(expand(p) for p in concatv(self._envs_dirs, fixed_dirs)))

    @property
    def pkgs_dirs(self):
        if self._pkgs_dirs:
            return tuple(IndexedSet(expand(p) for p in self._pkgs_dirs))
        else:
            cache_dir_name = 'pkgs32' if context.force_32bit else 'pkgs'
            return tuple(IndexedSet(expand(join(p, cache_dir_name)) for p in (
                self.root_prefix,
                self._user_data_dir,
            )))

    @property
    def _user_data_dir(self):
        if on_win:
            return user_data_dir(APP_NAME, APP_NAME)
        else:
            return expand(join('~', '.conda'))

    @property
    def private_envs_json_path(self):
        return join(self.root_prefix, "conda-meta", "private_envs")

    @property
    def default_prefix(self):
        _default_env = os.getenv('CONDA_DEFAULT_ENV')
        if _default_env in (None, ROOT_ENV_NAME):
            return self.root_prefix
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
        if self._root_dir:
            return abspath(expanduser(self._root_dir))
        elif conda_in_private_env():
            return normpath(join(self.conda_prefix, '..', '..'))
        else:
            return self.conda_prefix

    @property
    def conda_prefix(self):
        return sys.prefix

    @memoizedproperty
    def channel_alias(self):
        from ..models.channel import Channel
        location, scheme, auth, token = split_scheme_auth_token(self._channel_alias)
        return Channel(scheme=scheme, auth=auth, location=location, token=token)

    @property
    def migrated_channel_aliases(self):
        from ..models.channel import Channel
        return tuple(Channel(scheme=scheme, auth=auth, location=location, token=token)
                     for location, scheme, auth, token in
                     (split_scheme_auth_token(c) for c in self._migrated_channel_aliases))

    @property
    def prefix_specified(self):
        return (self._argparse_args.get("prefix") is not None and
                self._argparse_args.get("name") is not None)

    @memoizedproperty
    def default_channels(self):
        # the format for 'default_channels' is a list of strings that either
        #   - start with a scheme
        #   - are meant to be prepended with channel_alias
        return self.custom_multichannels[DEFAULTS_CHANNEL_NAME]

    @memoizedproperty
    def custom_multichannels(self):
        from ..models.channel import Channel

        reserved_multichannel_urls = odict((
            (DEFAULTS_CHANNEL_NAME, self._default_channels),
            ('local', self.conda_build_local_urls),
        ))
        reserved_multichannels = odict(
            (name, tuple(
                Channel.make_simple_channel(self.channel_alias, url) for url in urls)
             ) for name, urls in iteritems(reserved_multichannel_urls)
        )
        custom_multichannels = odict(
            (name, tuple(
                Channel.make_simple_channel(self.channel_alias, url) for url in urls)
             ) for name, urls in iteritems(self._custom_multichannels)
        )
        all_multichannels = odict(
            (name, channels)
            for name, channels in concat(map(iteritems, (
                custom_multichannels,
                reserved_multichannels,  # reserved comes last, so reserved overrides custom
            )))
        )
        return all_multichannels

    @memoizedproperty
    def custom_channels(self):
        from ..models.channel import Channel
        custom_channels = (Channel.make_simple_channel(self.channel_alias, url, name)
                           for name, url in iteritems(self._custom_channels))
        channels_from_multichannels = concat(channel for channel
                                             in itervalues(self.custom_multichannels))
        all_channels = odict((x.name, x) for x in (ch for ch in concatv(
            channels_from_multichannels,
            custom_channels,
        )))
        return all_channels

    @property
    def channels(self):
        # add 'defaults' channel when necessary if --channel is given via the command line
        if self._argparse_args and 'channel' in self._argparse_args:
            # TODO: it's args.channel right now, not channels
            argparse_channels = tuple(self._argparse_args['channel'] or ())
            if argparse_channels and argparse_channels == self._channels:
                return argparse_channels + (DEFAULTS_CHANNEL_NAME,)
        return self._channels


def conda_in_private_env():
    # conda is located in its own private environment named '_conda_'
    envs_dir, env_name = path_split(sys.prefix)
    return env_name == '_conda_' and basename(envs_dir) == 'envs'


def reset_context(search_path=SEARCH_PATH, argparse_args=None):
    context.__init__(search_path, APP_NAME, argparse_args)
    from ..models.channel import Channel
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
        'always_softlink': dals("""
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
        'client_ssl_cert': dals("""
            # client_ssl_cert can be a path pointing to a single file
            # containing the private key and the certificate (e.g. .pem),
            # or use 'client_ssl_cert_key' in conjuction with 'client_ssl_cert' for
            # individual files
            """),
        'client_ssl_cert_key': dals("""
            # used in conjunction with 'client_ssl_cert' for a matching key file
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
        'force_32bit': dals("""
            CONDA_FORCE_32BIT should only be used when running conda-build (in order
            to build 32-bit packages on a 64-bit system).  We don't want to mention it
            in the documentation, because it can mess up a lot of things.
        """)
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
    if getattr(args, 'name', None):
        if '/' in args.name:
            raise CondaValueError("'/' not allowed in environment name: %s" %
                                  args.name, getattr(args, 'json', False))
        if args.name == ROOT_ENV_NAME:
            return ctx.root_dir
        if search:
            return locate_prefix_by_name(ctx, args.name)
        else:
            # need first writable envs_dir
            envs_dir = first(ctx.envs_dirs, envs_dir_has_writable_pkg_cache)
            if not envs_dir:
                raise CondaError("No writable package envs directories found in\n"
                                 "%s" % text_type(context.envs_dirs))
            return join(envs_dir, args.name)
    elif getattr(args, 'prefix', None):
        return abspath(expanduser(args.prefix))
    else:
        return ctx.default_prefix


def envs_dir_has_writable_pkg_cache(envs_dir):
    from ..core.package_cache import PackageCache
    return PackageCache(join(dirname(envs_dir), 'pkgs')).is_writable


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
    for envs_dir in concatv(ctx.envs_dirs, (os.getcwd(),)):
        prefix = join(envs_dir, name)
        if isdir(prefix):
            return prefix

    raise CondaEnvironmentNotFoundError(name)


try:
    context = Context(SEARCH_PATH, APP_NAME, None)
except LoadError as e:
    print(e, file=sys.stderr)
    # Exception handler isn't loaded so use sys.exit
    sys.exit(1)
