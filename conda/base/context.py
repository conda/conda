# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import os
import sys
from collections import Sequence
from itertools import chain
from logging import getLogger
from os.path import abspath, basename, dirname, expanduser, isdir, join
from platform import machine
from requests.packages.urllib3.util import Url

try:
    from cytoolz.itertoolz import concatv
except ImportError:
    from .._vendor.toolz.itertoolz import concatv

from .constants import (DEFAULT_ANACONDA_API, DEFAULT_CHANNELS, DEFAULT_CHANNEL_ALIAS,
                        ROOT_ENV_NAME, SEARCH_PATH, conda)
from .._vendor.auxlib.compat import NoneType, string_types
from .._vendor.auxlib.ish import dals
from .._vendor.auxlib.path import expand
from ..common.url import path_to_url, split_scheme_auth_token, split_conda_url_easy_parts, urlparse, \
    join_url
from ..common.compat import iteritems, odict
from ..common.configuration import (Configuration, MapParameter, PrimitiveParameter,
                                    SequenceParameter)
from ..exceptions import CondaEnvironmentNotFoundError, CondaValueError

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
non_x86_linux_machines = {'armv6l', 'armv7l', 'ppc64le'}
_arch_names = {
    32: 'x86',
    64: 'x86_64',
}


def channel_alias_validation(value):
    from conda.models.channel import has_scheme
    if value and not has_scheme(value):
        return "channel_alias value '%s' must have scheme/protocol." % value
    return True


class Context(Configuration):

    add_pip_as_python_dependency = PrimitiveParameter(True)
    allow_softlinks = PrimitiveParameter(True)
    auto_update_conda = PrimitiveParameter(True, aliases=('self_update',))
    changeps1 = PrimitiveParameter(True)
    create_default_packages = SequenceParameter(string_types)
    disallow = SequenceParameter(string_types)
    force_32bit = PrimitiveParameter(False)
    track_features = SequenceParameter(string_types)
    use_pip = PrimitiveParameter(True)
    _root_dir = PrimitiveParameter(sys.prefix, aliases=('root_dir',))

    # connection details
    ssl_verify = PrimitiveParameter(True, parameter_type=string_types + (bool,))
    client_tls_cert = PrimitiveParameter('', aliases=('client_cert',))
    client_tls_cert_key = PrimitiveParameter('', aliases=('client_cert_key',))
    proxy_servers = MapParameter(string_types)

    add_anaconda_token = PrimitiveParameter(True, aliases=('add_binstar_token',))
    anaconda_site = PrimitiveParameter('')
    _channel_alias = PrimitiveParameter('', aliases=('channel_alias',),
                                        validation=channel_alias_validation)

    # channels
    channels = SequenceParameter(string_types, default=('defaults',))
    migrated_channel_aliases = SequenceParameter(string_types)  # TODO: also take a list of strings  # NOQA
    _default_channels = SequenceParameter(string_types, DEFAULT_CHANNELS, aliases=('default_channels',))
    _custom_channels = MapParameter(string_types, aliases=('custom_channels',))
    migrated_custom_channels = MapParameter(string_types)  # TODO: also take a list of strings
    _custom_multichannels = MapParameter(Sequence, aliases=('custom_multichannels',))

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
    def default_python(self):
        ver = sys.version_info
        return '%d.%d' % (ver.major, ver.minor)

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
    def channel_alias(self):
        if self.conda_repo_token:
            return join_url(self.conda_repo_url, 't', self.conda_repo_token)
        else:
            return self.conda_repo_url

    @property
    def binstar_api_url(self):
        if 'binstar_api_url' not in self._cache:
            self._set_channel_alias_and_token()
        return self._cache['binstar_api_url']

    @property
    def conda_repo_url(self):
        if 'conda_repo_url' not in self._cache:
            self._set_channel_alias_and_token()
        return self._cache['conda_repo_url']

    @property
    def conda_repo_token(self):
        if 'conda_repo_token' not in self._cache:
            self._set_channel_alias_and_token()
        return self._cache['conda_repo_token']

    @property
    def default_channels(self):
        # the format for 'default_channels' is a list of strings that either
        #   - start with a scheme
        #   - are meant to be prepended with channel_alias
        from conda.models.channel import Channel
        from conda.models.channel import has_scheme
        ca_location, ca_scheme, ca_auth, ca_token = split_scheme_auth_token(self.channel_alias)

        def make_simple_Channel(channel):
            if has_scheme(channel):
                scheme, auth, token, platform, package_filename, host, port, path, query = split_conda_url_easy_parts(channel)
                test_url = Url(host=host, port=port, path=path).url
                if test_url.startswith(ca_location):
                    location, name = ca_location, test_url.replace(ca_location, '', 1)
                else:
                    location, name = Url(host=host, port=port).url, path
                return Channel(scheme=scheme, auth=auth, location=location, token=token, name=name.strip('/'))
            else:
                return Channel(scheme=ca_scheme, auth=ca_auth, location=ca_location, token=ca_token, name=channel)

        return tuple(make_simple_Channel(v) for v in self._default_channels)

    @property
    def local_build_root_channel(self):
        from ..models.channel import Channel
        url_parts = urlparse(path_to_url(self.local_build_root))
        location, name = url_parts.path.rsplit('/', 1)
        if not location:
            location = '/'
        assert name == 'conda-bld'
        return Channel(scheme=url_parts.scheme, location=location, name=name)

    @property
    def custom_multichannels(self):
        from ..models.channel import Channel
        default_custom_multichannels = {
            'defaults': self.default_channels,
            'local': (self.local_build_root_channel,),
        }
        return odict((name, tuple(Channel(v) for v in c))
                     for name, c in concatv(iteritems(default_custom_multichannels),
                                            iteritems(self._custom_multichannels)))
    @property
    def custom_channels(self):
        from ..models.channel import Channel
        from conda.models.channel import has_scheme
        ca_location, ca_scheme, ca_auth, ca_token = split_scheme_auth_token(self.channel_alias)

        def make_simple_custom_Channel(name, url):
            if has_scheme(url):
                scheme, auth, token, platform, package_filename, host, port, path, query = split_conda_url_easy_parts(url)
                location = Url(host=host, port=port, path=path).url
                return Channel(scheme=scheme, auth=auth, location=location, token=token, name=name.strip('/'))
            else:
                return Channel(scheme=ca_scheme, auth=ca_auth, location=ca_location, token=ca_token, name=name.strip('/'))


        return odict((x.name, x) for x in
                     (ch for ch in concatv(self.default_channels,
                                                    (self.local_build_root_channel,),
                                                    (make_simple_custom_Channel(k, v) for k, v in iteritems(self._custom_channels)),
                                                    )))

    def _set_channel_alias_and_token(self):
        from ..gateways.anaconda_client import (get_anaconda_site_components,
                                                get_channel_url_components,
                                                binstar_load_token)

        # Step 1. Use 'channel_alias' config parameter if set.
        if self._channel_alias:
            binstar_url, conda_url, token = get_channel_url_components(self._channel_alias)

        # Step 2. If the 'anaconda_site' configuration parameter is set, use that.
        elif self.anaconda_site:
            binstar_url, conda_url, token = get_anaconda_site_components(self.anaconda_site)

        # Step 3. Use DEFAULT_CHANNEL_ALIAS
        else:
            binstar_url, conda_url = DEFAULT_ANACONDA_API, DEFAULT_CHANNEL_ALIAS
            token = binstar_load_token(binstar_url)

        self._cache['binstar_api_url'] = binstar_url
        self._cache['conda_repo_url'] = conda_url
        self._cache['conda_repo_token'] = token


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
        'client_tls_cert': dals("""
            # client_tls_cert can be a path pointing to a single file
            # containing the private key and the certificate (e.g. .pem),
            # or use 'client_tls_cert_key' in conjuction with 'client_tls_cert' for individual files
            """),
        'client_tls_cert_key': dals("""
            # used in conjunction with 'client_tls_cert' for a matching key file
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
