# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from errno import ENOENT
from logging import getLogger
import os
from os.path import (abspath, basename, dirname, expanduser, isdir, isfile, join, normpath,
                     split as path_split)
from platform import machine
import sys

from .constants import (APP_NAME, DEFAULTS_CHANNEL_NAME, DEFAULT_AGGRESSIVE_UPDATE_PACKAGES,
                        DEFAULT_CHANNELS, DEFAULT_CHANNEL_ALIAS, ERROR_UPLOAD_URL,
                        PLATFORM_DIRECTORIES, PREFIX_MAGIC_FILE, PathConflict, ROOT_ENV_NAME,
                        SEARCH_PATH, SafetyChecks)
from .. import __version__ as CONDA_VERSION
from .._vendor.appdirs import user_data_dir
from .._vendor.auxlib.collection import frozendict
from .._vendor.auxlib.decorators import memoize, memoizedproperty
from .._vendor.auxlib.ish import dals
from .._vendor.boltons.setutils import IndexedSet
from ..common.compat import NoneType, iteritems, itervalues, odict, on_win, string_types
from ..common.configuration import (Configuration, LoadError, MapParameter, PrimitiveParameter,
                                    SequenceParameter, ValidationError)
from ..common.disk import conda_bld_ensure_dir
from ..common.path import expand
from ..common.platform import linux_get_libc_version
from ..common.url import has_scheme, path_to_url, split_scheme_auth_token

try:
    from cytoolz.itertoolz import concat, concatv, unique
except ImportError:  # pragma: no cover
    from .._vendor.toolz.itertoolz import concat, concatv, unique

try:
    os.getcwd()
except (IOError, OSError) as e:
    if e.errno == ENOENT:
        # FileNotFoundError can occur when cwd has been deleted out from underneath the process.
        # To resolve #6584, let's go with setting cwd to sys.prefix, and see how far we get.
        os.chdir(sys.prefix)
    else:
        raise

log = getLogger(__name__)

_platform_map = {
    'linux2': 'linux',
    'linux': 'linux',
    'darwin': 'osx',
    'win32': 'win',
    'zos': 'zos',
}
non_x86_linux_machines = {
    'armv6l',
    'armv7l',
    'aarch64',
    'ppc64le',
}
_arch_names = {
    32: 'x86',
    64: 'x86_64',
}

user_rc_path = abspath(expanduser('~/.condarc'))
sys_rc_path = join(sys.prefix, '.condarc')


def channel_alias_validation(value):
    if value and not has_scheme(value):
        return "channel_alias value '%s' must have scheme/protocol." % value
    return True


def default_python_default():
    ver = sys.version_info
    return '%d.%d' % (ver.major, ver.minor)


def default_python_validation(value):
    if value:
        if len(value) == 3 and value[1] == '.':
            try:
                value = float(value)
                if 2.0 <= value < 4.0:
                    return True
            except ValueError:  # pragma: no cover
                pass
    else:
        # Set to None or '' meaning no python pinning
        return True

    return "default_python value '%s' not of the form '[23].[0-9]' or ''" % value


def ssl_verify_validation(value):
    if isinstance(value, string_types):
        if not isfile(value) and not isdir(value):
            return ("ssl_verify value '%s' must be a boolean, a path to a "
                    "certificate bundle file, or a path to a directory containing "
                    "certificates of trusted CAs." % value)
    return True


class Context(Configuration):

    add_pip_as_python_dependency = PrimitiveParameter(True)
    allow_cycles = PrimitiveParameter(True)  # allow cyclical dependencies, or raise
    allow_softlinks = PrimitiveParameter(False)
    auto_update_conda = PrimitiveParameter(True, aliases=('self_update',))
    notify_outdated_conda = PrimitiveParameter(True)
    clobber = PrimitiveParameter(False)
    changeps1 = PrimitiveParameter(True)
    create_default_packages = SequenceParameter(string_types)
    default_python = PrimitiveParameter(default_python_default(),
                                        element_type=string_types + (NoneType,),
                                        validation=default_python_validation)
    download_only = PrimitiveParameter(False)
    enable_private_envs = PrimitiveParameter(False)
    force_32bit = PrimitiveParameter(False)
    max_shlvl = PrimitiveParameter(2)
    non_admin_enabled = PrimitiveParameter(True)

    # Safety & Security
    _aggressive_update_packages = SequenceParameter(string_types,
                                                    DEFAULT_AGGRESSIVE_UPDATE_PACKAGES,
                                                    aliases=('aggressive_update_packages',))
    safety_checks = PrimitiveParameter(SafetyChecks.warn)
    path_conflict = PrimitiveParameter(PathConflict.clobber)

    pinned_packages = SequenceParameter(string_types, string_delimiter='&')  # TODO: consider a different string delimiter  # NOQA
    disallowed_packages = SequenceParameter(string_types, aliases=('disallow',),
                                            string_delimiter='&')
    rollback_enabled = PrimitiveParameter(True)
    track_features = SequenceParameter(string_types)
    use_pip = PrimitiveParameter(True)
    use_index_cache = PrimitiveParameter(False)

    _root_prefix = PrimitiveParameter("", aliases=('root_dir', 'root_prefix'))
    _envs_dirs = SequenceParameter(string_types, aliases=('envs_dirs', 'envs_path'),
                                   string_delimiter=os.pathsep)
    _pkgs_dirs = SequenceParameter(string_types, aliases=('pkgs_dirs',))
    _subdir = PrimitiveParameter('', aliases=('subdir',))
    _subdirs = SequenceParameter(string_types, aliases=('subdirs',))

    local_repodata_ttl = PrimitiveParameter(1, element_type=(bool, int))
    # number of seconds to cache repodata locally
    #   True/1: respect Cache-Control max-age header
    #   False/0: always fetch remote repodata (HTTP 304 responses respected)

    # remote connection details
    ssl_verify = PrimitiveParameter(True, element_type=string_types + (bool,),
                                    aliases=('verify_ssl',),
                                    validation=ssl_verify_validation)
    client_ssl_cert = PrimitiveParameter(None, aliases=('client_cert',),
                                         element_type=string_types + (NoneType,))
    client_ssl_cert_key = PrimitiveParameter(None, aliases=('client_cert_key',),
                                             element_type=string_types + (NoneType,))
    proxy_servers = MapParameter(string_types + (NoneType,))
    remote_connect_timeout_secs = PrimitiveParameter(9.15)
    remote_read_timeout_secs = PrimitiveParameter(60.)
    remote_max_retries = PrimitiveParameter(3)

    add_anaconda_token = PrimitiveParameter(True, aliases=('add_binstar_token',))

    # #############################
    # channels
    # #############################
    allow_non_channel_urls = PrimitiveParameter(False)
    _channel_alias = PrimitiveParameter(DEFAULT_CHANNEL_ALIAS,
                                        aliases=('channel_alias',),
                                        validation=channel_alias_validation)
    channel_priority = PrimitiveParameter(True)
    _channels = SequenceParameter(string_types, default=(DEFAULTS_CHANNEL_NAME,),
                                  aliases=('channels', 'channel',))  # channel for args.channel
    _custom_channels = MapParameter(string_types, aliases=('custom_channels',))
    _custom_multichannels = MapParameter(list, aliases=('custom_multichannels',))
    _default_channels = SequenceParameter(string_types, DEFAULT_CHANNELS,
                                          aliases=('default_channels',))
    _migrated_channel_aliases = SequenceParameter(string_types,
                                                  aliases=('migrated_channel_aliases',))  # TODO: also take a list of strings # NOQA
    migrated_custom_channels = MapParameter(string_types)  # TODO: also take a list of strings
    override_channels_enabled = PrimitiveParameter(True)
    show_channel_urls = PrimitiveParameter(None, element_type=(bool, NoneType))
    use_local = PrimitiveParameter(False)
    whitelist_channels = SequenceParameter(string_types)

    always_softlink = PrimitiveParameter(False, aliases=('softlink',))
    always_copy = PrimitiveParameter(False, aliases=('copy',))
    always_yes = PrimitiveParameter(None, aliases=('yes',), element_type=(bool, NoneType))
    debug = PrimitiveParameter(False)
    dry_run = PrimitiveParameter(False)
    error_upload_url = PrimitiveParameter(ERROR_UPLOAD_URL)
    force = PrimitiveParameter(False)
    json = PrimitiveParameter(False)
    no_dependencies = PrimitiveParameter(False, aliases=('no_deps',))
    offline = PrimitiveParameter(False)
    only_dependencies = PrimitiveParameter(False, aliases=('only_deps',))
    quiet = PrimitiveParameter(False)
    prune = PrimitiveParameter(False)
    ignore_pinned = PrimitiveParameter(False)
    report_errors = PrimitiveParameter(None, element_type=(bool, NoneType))
    shortcuts = PrimitiveParameter(True)
    update_dependencies = PrimitiveParameter(False, aliases=('update_deps',))
    _verbosity = PrimitiveParameter(0, aliases=('verbose', 'verbosity'), element_type=int)

    target_prefix_override = PrimitiveParameter('')

    # conda_build
    bld_path = PrimitiveParameter('')
    anaconda_upload = PrimitiveParameter(None, aliases=('binstar_upload',),
                                         element_type=(bool, NoneType))
    _croot = PrimitiveParameter('', aliases=('croot',))
    conda_build = MapParameter(string_types, aliases=('conda-build',))

    def __init__(self, search_path=None, argparse_args=None):
        if search_path is None:
            search_path = SEARCH_PATH

        if argparse_args:
            # This block of code sets CONDA_PREFIX based on '-n' and '-p' flags, so that
            # configuration can be properly loaded from those locations
            func_name = ('func' in argparse_args and argparse_args.func or '').rsplit('.', 1)[-1]
            if func_name in ('create', 'install', 'update', 'remove', 'uninstall', 'upgrade'):
                if 'prefix' in argparse_args and argparse_args.prefix:
                    os.environ['CONDA_PREFIX'] = argparse_args.prefix
                elif 'name' in argparse_args and argparse_args.name:
                    # Currently, usage of the '-n' flag is inefficient, with all configuration
                    # files being loaded/re-loaded at least two times.
                    target_prefix = determine_target_prefix(context, argparse_args)
                    if target_prefix != context.root_prefix:
                        os.environ['CONDA_PREFIX'] = determine_target_prefix(context,
                                                                             argparse_args)

        super(Context, self).__init__(search_path=search_path, app_name=APP_NAME,
                                      argparse_args=argparse_args)

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
    def local_build_root(self):
        return self.croot

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
    def conda_private(self):
        return conda_in_private_env()

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
        elif self.platform == 'zos':
            return 'zos-z'
        else:
            return '%s-%d' % (self.platform, self.bits)

    @property
    def subdirs(self):
        return self._subdirs if self._subdirs else (self.subdir, 'noarch')

    @memoizedproperty
    def known_subdirs(self):
        return frozenset(concatv(PLATFORM_DIRECTORIES, self.subdirs))

    @property
    def bits(self):
        if self.force_32bit:
            return 32
        else:
            return 8 * tuple.__itemsize__

    @property
    def root_dir(self):
        # root_dir is an alias for root_prefix, we prefer the name "root_prefix"
        # because it is more consistent with other names
        return self.root_prefix

    @property
    def root_writable(self):
        # rather than using conda.gateways.disk.test.prefix_is_writable
        # let's shortcut and assume the root prefix exists
        path = join(self.root_prefix, PREFIX_MAGIC_FILE)
        if isfile(path):
            try:
                fh = open(path, 'a+')
            except (IOError, OSError) as e:
                log.debug(e)
                return False
            else:
                fh.close()
                return True
        return False

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
                join(self._user_data_dir, 'envs'),
                join(self.root_prefix, 'envs'),
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

    @memoizedproperty
    def trash_dir(self):
        # TODO: this inline import can be cleaned up by moving pkgs_dir write detection logic
        from ..core.package_cache_data import PackageCacheData
        pkgs_dir = PackageCacheData.first_writable().pkgs_dir
        trash_dir = join(pkgs_dir, '.trash')
        from ..gateways.disk.create import mkdir_p
        mkdir_p(trash_dir)
        return trash_dir

    @property
    def _user_data_dir(self):
        if on_win:
            return user_data_dir(APP_NAME, APP_NAME)
        else:
            return expand(join('~', '.conda'))

    @property
    def default_prefix(self):
        if self.active_prefix:
            return self.active_prefix
        _default_env = os.getenv('CONDA_DEFAULT_ENV')
        if _default_env in (None, ROOT_ENV_NAME, 'root'):
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
    def active_prefix(self):
        return os.getenv('CONDA_PREFIX')

    @property
    def shlvl(self):
        return int(os.getenv('CONDA_SHLVL', -1))

    @property
    def aggressive_update_packages(self):
        from ..models.match_spec import MatchSpec
        return tuple(MatchSpec(s, optional=True) for s in self._aggressive_update_packages)

    @property
    def deps_modifier(self):
        from ..core.solve import DepsModifier
        if self.update_dependencies and self.only_dependencies:
            return DepsModifier.UPDATE_DEPS_ONLY_DEPS
        elif self.update_dependencies:
            return DepsModifier.UPDATE_DEPS
        elif self.only_dependencies:
            return DepsModifier.ONLY_DEPS
        elif self.no_dependencies:
            return DepsModifier.NO_DEPS
        elif self._argparse_args and 'all' in self._argparse_args and self._argparse_args.all:
            return DepsModifier.UPDATE_ALL
        else:
            return None

    @property
    def target_prefix(self):
        # used for the prefix that is the target of the command currently being executed
        # different from the active prefix, which is sometimes given by -p or -n command line flags
        return determine_target_prefix(self)

    @memoizedproperty
    def root_prefix(self):
        if self._root_prefix:
            return abspath(expanduser(self._root_prefix))
        elif conda_in_private_env():
            return normpath(join(self.conda_prefix, '..', '..'))
        else:
            return self.conda_prefix

    @property
    def conda_prefix(self):
        return normpath(sys.prefix)

    @property
    def conda_exe(self):
        bin_dir = 'Scripts' if on_win else 'bin'
        exe = 'conda.exe' if on_win else 'conda'
        return join(self.conda_prefix, bin_dir, exe)

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
        return (self._argparse_args.get("prefix") is not None or
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
        local_add = ('local',) if self.use_local else ()
        if (self._argparse_args and 'override_channels' in self._argparse_args
                and self._argparse_args['override_channels']):
            if not self.override_channels_enabled:
                from ..exceptions import OperationNotAllowed
                raise OperationNotAllowed(dals("""
                Overriding channels has been disabled.
                """))
            elif not (self._argparse_args and 'channel' in self._argparse_args
                      and self._argparse_args['channel']):
                from ..exceptions import CommandArgumentError
                raise CommandArgumentError(dals("""
                At least one -c / --channel flag must be supplied when using --override-channels.
                """))
            else:
                return tuple(IndexedSet(concatv(local_add, self._argparse_args['channel'])))

        # add 'defaults' channel when necessary if --channel is given via the command line
        if self._argparse_args and 'channel' in self._argparse_args:
            # TODO: it's args.channel right now, not channels
            argparse_channels = tuple(self._argparse_args['channel'] or ())
            if argparse_channels and argparse_channels == self._channels:
                return tuple(IndexedSet(concatv(local_add, argparse_channels,
                                                (DEFAULTS_CHANNEL_NAME,))))
        return tuple(IndexedSet(concatv(local_add, self._channels)))

    def get_descriptions(self):
        return get_help_dict()

    def list_parameters(self):
        UNLISTED_PARAMETERS = (
            'allow_cycles',  # allow cyclical dependencies, or raise
            'bld_path',
            'conda_build',
            'croot',
            'debug',
            'default_python',
            'dry_run',
            'enable_private_envs',
            'error_upload_url',  # should remain undocumented
            'force_32bit',
            'ignore_pinned',
            'migrated_custom_channels',
            'only_dependencies',
            'prune',
            'root_prefix',
            'subdir',
            'subdirs',
# https://conda.io/docs/config.html#disable-updating-of-dependencies-update-dependencies # NOQA
# I don't think this documentation is correct any longer. # NOQA
            'target_prefix_override',  # used to override prefix rewriting, for e.g. building docker containers or RPMs  # NOQA
            'update_dependencies',
            'use_local',
        )
        return tuple(p for p in super(Context, self).list_parameters()
                     if p not in UNLISTED_PARAMETERS)

    @property
    def binstar_upload(self):
        # backward compatibility for conda-build
        return self.anaconda_upload

    @property
    def user_agent(self):
        return _get_user_agent(self.platform)

    @property
    def verbosity(self):
        return 2 if self.debug else self._verbosity


def conda_in_private_env():
    # conda is located in its own private environment named '_conda_'
    envs_dir, env_name = path_split(sys.prefix)
    return env_name == '_conda_' and basename(envs_dir) == 'envs'


def reset_context(search_path=SEARCH_PATH, argparse_args=None):
    context.__init__(search_path, argparse_args)
    from ..models.channel import Channel
    Channel._reset_state()
    # need to import here to avoid circular dependency
    return context


@memoize
def get_help_dict():
    # this is a function so that most of the time it's not evaluated and loaded into memory
    return frozendict({
        'add_anaconda_token': dals("""
            In conjunction with the anaconda command-line client (installed with
            `conda install anaconda-client`), and following logging into an Anaconda
            Server API site using `anaconda login`, automatically apply a matching
            private token to enable access to private packages and channels.
            """),
        'add_pip_as_python_dependency': dals("""
            Add pip, wheel and setuptools as dependencies of python. This ensures pip,
            wheel and setuptools will always be installed any time python is installed.
            """),
        'aggressive_update_packages': dals("""
            A list of packages that, if installed, are always updated to the latest possible
            version.
            """),
        'allow_non_channel_urls': dals("""
            Warn, but do not fail, when conda detects a channel url is not a valid channel.
            """),
        'allow_softlinks': dals("""
            When allow_softlinks is True, conda uses hard-links when possible, and soft-links
            (symlinks) when hard-links are not possible, such as when installing on a
            different filesystem than the one that the package cache is on. When
            allow_softlinks is False, conda still uses hard-links when possible, but when it
            is not possible, conda copies files. Individual packages can override
            this setting, specifying that certain files should never be soft-linked (see the
            no_link option in the build recipe documentation).
            """),
        'always_copy': dals("""
            Register a preference that files be copied into a prefix during install rather
            than hard-linked.
            """),
        'always_softlink': dals("""
            Register a preference that files be soft-linked (symlinked) into a prefix during
            install rather than hard-linked. The link source is the 'pkgs_dir' package cache
            from where the package is being linked. WARNING: Using this option can result in
            corruption of long-lived conda environments. Package caches are *caches*, which
            means there is some churn and invalidation. With this option, the contents of
            environments can be switched out (or erased) via operations on other environments.
            """),
        'always_yes': dals("""
            Automatically choose the 'yes' option whenever asked to proceed with a conda
            operation, such as when running `conda install`.
            """),
        'anaconda_upload': dals("""
            Automatically upload packages built with conda build to anaconda.org.
            """),
        'auto_update_conda': dals("""
            Automatically update conda when a newer or higher priority version is detected.
            """),
        'changeps1': dals("""
            When using activate, change the command prompt ($PS1) to include the
            activated environment.
            """),
        'channel_alias': dals("""
            The prepended url location to associate with channel names.
            """),
        'channel_priority': dals("""
            When True, the solver is instructed to prefer channel order over package
            version. When False, the solver is instructed to give package version
            preference over channel priority.
            """),
        'channels': dals("""
            The list of conda channels to include for relevant operations.
            """),
        'client_ssl_cert': dals("""
            A path to a single file containing a private key and certificate (e.g. .pem
            file). Alternately, use client_ssl_cert_key in conjuction with client_ssl_cert
            for individual files.
            """),
        'client_ssl_cert_key': dals("""
            Used in conjunction with client_ssl_cert for a matching key file.
            """),
        'clobber': dals("""
            Allow clobbering of overlapping file paths within packages, and suppress
            related warnings. Overrides the path_conflict configuration value when
            set to 'warn' or 'prevent'.
            """),
        'create_default_packages': dals("""
            Packages that are by default added to a newly created environments.
            """),  # TODO: This is a bad parameter name. Consider an alternate.
        'custom_channels': dals("""
            A map of key-value pairs where the key is a channel name and the value is
            a channel location. Channels defined here override the default
            'channel_alias' value. The channel name (key) is not included in the channel
            location (value).  For example, to override the location of the 'conda-forge'
            channel where the url to repodata is
            https://anaconda-repo.dev/packages/conda-forge/linux-64/repodata.json, add an
            entry 'conda-forge: https://anaconda-repo.dev/packages'.
            """),
        'custom_multichannels': dals("""
            A multichannel is a metachannel composed of multiple channels. The two reserved
            multichannels are 'defaults' and 'local'. The 'defaults' multichannel is
            customized using the 'default_channels' parameter. The 'local'
            multichannel is a list of file:// channel locations where conda-build stashes
            successfully-built packages.  Other multichannels can be defined with
            custom_multichannels, where the key is the multichannel name and the value is
            a list of channel names and/or channel urls.
            """),
        'default_channels': dals("""
            The list of channel names and/or urls used for the 'defaults' multichannel.
            """),
        # 'default_python': dals("""
        #     specifies the default major & minor version of Python to be used when
        #     building packages with conda-build. Also used to determine the major
        #     version of Python (2/3) to be used in new environments. Defaults to
        #     the version used by conda itself.
        #     """),
        'disallowed_packages': dals("""
            Package specifications to disallow installing. The default is to allow
            all packages.
            """),
        'download_only': dals("""
            Solve an environment and ensure package caches are populated, but exit
            prior to unlinking and linking packages into the prefix
            """),
        'envs_dirs': dals("""
            The list of directories to search for named environments. When creating a new
            named environment, the environment will be placed in the first writable
            location.
            """),
        'force': dals("""
            Override any of conda's objections and safeguards for installing packages and
            potentially breaking environments. Also re-installs the package, even if the
            package is already installed. Implies --no-deps.
            """),
        # 'force_32bit': dals("""
        #     CONDA_FORCE_32BIT should only be used when running conda-build (in order
        #     to build 32-bit packages on a 64-bit system).  We don't want to mention it
        #     in the documentation, because it can mess up a lot of things.
        #     """),
        'json': dals("""
            Ensure all output written to stdout is structured json.
            """),
        'local_repodata_ttl': dals("""
            For a value of False or 0, always fetch remote repodata (HTTP 304 responses
            respected). For a value of True or 1, respect the HTTP Cache-Control max-age
            header. Any other positive integer values is the number of seconds to locally
            cache repodata before checking the remote server for an update.
            """),
        'max_shlvl': dals("""
            The maximum number of stacked active conda environments.
            """),
        'migrated_channel_aliases': dals("""
            A list of previously-used channel_alias values, useful for example when switching
            between different Anaconda Repository instances.
            """),
        'no_dependencies': dals("""
            Do not install, update, remove, or change dependencies. This WILL lead to broken
            environments and inconsistent behavior. Use at your own risk.
            """),
        'non_admin_enabled': dals("""
            Allows completion of conda's create, install, update, and remove operations, for
            non-privileged (non-root or non-administrator) users.
            """),
        'notify_outdated_conda': dals("""
            Notify if a newer version of conda is detected during a create, install, update,
            or remove operation.
            """),
        'offline': dals("""
            Restrict conda to cached download content and file:// based urls.
            """),
        'override_channels_enabled': dals("""
            Permit use of the --overide-channels command-line flag.
            """),
        'path_conflict': dals("""
            The method by which conda handle's conflicting/overlapping paths during a
            create, install, or update operation. The value must be one of 'clobber',
            'warn', or 'prevent'. The '--clobber' command-line flag or clobber
            configuration parameter overrides path_conflict set to 'prevent'.
            """),
        'pinned_packages': dals("""
            A list of package specs to pin for every environment resolution.
            This parameter is in BETA, and its behavior may change in a future release.
            """),
        'pkgs_dirs': dals("""
            The list of directories where locally-available packages are linked from at
            install time. Packages not locally available are downloaded and extracted
            into the first writable directory.
            """),
        'proxy_servers': dals("""
            A mapping to enable proxy settings. Keys can be either (1) a scheme://hostname
            form, which will match any request to the given scheme and exact hostname, or
            (2) just a scheme, which will match requests to that scheme. Values are are
            the actual proxy server, and are of the form
            'scheme://[user:password@]host[:port]'. The optional 'user:password' inclusion
            enables HTTP Basic Auth with your proxy.
            """),
        'quiet': dals("""
            Disable progress bar display and other output.
            """),
        'remote_connect_timeout_secs': dals("""
            The number seconds conda will wait for your client to establish a connection
            to a remote url resource.
            """),
        'remote_max_retries': dals("""
            The maximum number of retries each HTTP connection should attempt.
            """),
        'remote_read_timeout_secs': dals("""
            Once conda has connected to a remote resource and sent an HTTP request, the
            read timeout is the number of seconds conda will wait for the server to send
            a response.
            """),
        'report_errors': dals("""
            Opt in, or opt out, of automatic error reporting to core maintainers. Error
            reports are anonymous, with only the error stack trace and information given
            by `conda info` being sent.
            """),
        'rollback_enabled': dals("""
            Should any error occur during an unlink/link transaction, revert any disk
            mutations made to that point in the transaction.
            """),
        'safety_checks': dals("""
            Enforce available safety guarantees during package installation.
            The value must be one of 'enabled', 'warn', or 'disabled'.
            """),
        'shortcuts': dals("""
            Allow packages to create OS-specific shortcuts (e.g. in the Windows Start
            Menu) at install time.
            """),
        'show_channel_urls': dals("""
            Show channel URLs when displaying what is going to be downloaded.
            """),
        'ssl_verify': dals("""
            Conda verifies SSL certificates for HTTPS requests, just like a web
            browser. By default, SSL verification is enabled, and conda operations will
            fail if a required url's certificate cannot be verified. Setting ssl_verify to
            False disables certification verificaiton. The value for ssl_verify can also
            be (1) a path to a CA bundle file, or (2) a path to a directory containing
            certificates of trusted CA.
            """),
        'track_features': dals("""
            A list of features that are tracked by default. An entry here is similar to
            adding an entry to the create_default_packages list.
            """),
        'use_index_cache': dals("""
            Use cache of channel index files, even if it has expired.
            """),
        'use_pip': dals("""
            Include non-conda-installed python packages with conda list. This does not
            affect any conda command or functionality other than the output of the
            command conda list.
            """),
        'verbosity': dals("""
            Sets output log level. 0 is warn. 1 is info. 2 is debug. 3 is trace.
            """),
        'whitelist_channels': dals("""
            The exclusive list of channels allowed to be used on the system. Use of any
            other channels will result in an error. If conda-build channels are to be
            allowed, along with the --use-local command line flag, be sure to include the
            'local' channel in the list. If the list is empty or left undefined, no
            channel exclusions will be enforced.
            """)
    })


@memoize
def _get_user_agent(context_platform):
    import platform
    try:
        from requests import __version__ as REQUESTS_VERSION
    except ImportError:  # pragma: no cover
        try:
            from pip._vendor.requests import __version__ as REQUESTS_VERSION
        except ImportError:
            REQUESTS_VERSION = "unknown"

    _user_agent = ("conda/{conda_ver} "
                   "requests/{requests_ver} "
                   "{python}/{py_ver} "
                   "{system}/{kernel} {dist}/{ver}")

    libc_family, libc_ver = linux_get_libc_version()
    if context_platform == 'linux':
        from .._vendor.distro import linux_distribution
        try:
            distinfo = linux_distribution(full_distribution_name=False)
        except Exception as e:
            log.debug('%r', e, exc_info=True)
            distinfo = ('Linux', 'unknown')
        dist, ver = distinfo[0], distinfo[1]
    elif context_platform == 'osx':
        dist = 'OSX'
        ver = platform.mac_ver()[0]
    else:
        dist = platform.system()
        ver = platform.version()

    user_agent = _user_agent.format(conda_ver=CONDA_VERSION,
                                    requests_ver=REQUESTS_VERSION,
                                    python=platform.python_implementation(),
                                    py_ver=platform.python_version(),
                                    system=platform.system(), kernel=platform.release(),
                                    dist=dist, ver=ver)
    if libc_ver:
        user_agent += " {}/{}".format(libc_family, libc_ver)
    return user_agent


def locate_prefix_by_name(name, envs_dirs=None):
    """Find the location of a prefix given a conda env name.  If the location does not exist, an
    error is raised.
    """
    assert name
    if name in (ROOT_ENV_NAME, 'root'):
        return context.root_prefix
    if envs_dirs is None:
        envs_dirs = context.envs_dirs
    for envs_dir in envs_dirs:
        if not isdir(envs_dir):
            continue
        prefix = join(envs_dir, name)
        if isdir(prefix):
            return prefix

    from ..exceptions import EnvironmentNameNotFound
    raise EnvironmentNameNotFound(name)


def determine_target_prefix(ctx, args=None):
    """Get the prefix to operate in.  The prefix may not yet exist.

    Args:
        ctx: the context of conda
        args: the argparse args from the command line

    Returns: the prefix
    Raises: CondaEnvironmentNotFoundError if the prefix is invalid
    """

    argparse_args = args or ctx._argparse_args
    try:
        prefix_name = argparse_args.name
    except AttributeError:
        prefix_name = None
    try:
        prefix_path = argparse_args.prefix
    except AttributeError:
        prefix_path = None

    if prefix_name is not None and not prefix_name.strip():  # pragma: no cover
        from ..exceptions import ArgumentError
        raise ArgumentError("Argument --name requires a value.")

    if prefix_path is not None and not prefix_path.strip():  # pragma: no cover
        from ..exceptions import ArgumentError
        raise ArgumentError("Argument --prefix requires a value.")

    if prefix_name is None and prefix_path is None:
        return ctx.default_prefix
    elif prefix_path is not None:
        return expand(prefix_path)
    else:
        if '/' in prefix_name:
            from ..exceptions import CondaValueError
            raise CondaValueError("'/' not allowed in environment name: %s" %
                                  prefix_name)
        if prefix_name in (ROOT_ENV_NAME, 'root'):
            return ctx.root_prefix
        else:
            from ..exceptions import EnvironmentNameNotFound
            try:
                return locate_prefix_by_name(prefix_name)
            except EnvironmentNameNotFound:
                return join(_first_writable_envs_dir(), prefix_name)


def _first_writable_envs_dir():
    # Starting in conda 4.3, we use the writability test on '..../pkgs/url.txt' to determine
    # writability of '..../envs'.
    from ..core.package_cache_data import PackageCacheData
    for envs_dir in context.envs_dirs:
        pkgs_dir = join(dirname(envs_dir), 'pkgs')
        if PackageCacheData(pkgs_dir).is_writable:
            return envs_dir

    from ..exceptions import NotWritableError
    raise NotWritableError(context.envs_dirs[0], None)


# backward compatibility for conda-build
def get_prefix(ctx, args, search=True):  # pragma: no cover
    return determine_target_prefix(ctx or context, args)


try:
    context = Context((), None)
except LoadError as e:  # pragma: no cover
    print(e, file=sys.stderr)
    # Exception handler isn't loaded so use sys.exit
    sys.exit(1)
