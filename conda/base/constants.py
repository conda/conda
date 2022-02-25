# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
This file should hold most string literals and magic numbers used throughout the code base.
The exception is if a literal is specifically meant to be private to and isolated within a module.
Think of this as a "more static" source of configuration information.

Another important source of "static" configuration is conda/models/enums.py.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

from enum import Enum, EnumMeta
from os.path import join
import struct

from ..common.compat import itervalues, on_win, six_with_metaclass, string_types

PREFIX_PLACEHOLDER = ('/opt/anaconda1anaconda2'
                      # this is intentionally split into parts, such that running
                      # this program on itself will leave it unchanged
                      'anaconda3')

machine_bits = 8 * struct.calcsize("P")

APP_NAME = 'conda'

if on_win:
    SEARCH_PATH = (
        'C:/ProgramData/conda/.condarc',
        'C:/ProgramData/conda/condarc',
        'C:/ProgramData/conda/condarc.d',
    )
else:
    SEARCH_PATH = (
        '/etc/conda/.condarc',
        '/etc/conda/condarc',
        '/etc/conda/condarc.d/',
        '/var/lib/conda/.condarc',
        '/var/lib/conda/condarc',
        '/var/lib/conda/condarc.d/',
    )

SEARCH_PATH += (
    '$CONDA_ROOT/.condarc',
    '$CONDA_ROOT/condarc',
    '$CONDA_ROOT/condarc.d/',
    '$XDG_CONFIG_HOME/conda/.condarc',
    '$XDG_CONFIG_HOME/conda/condarc',
    '$XDG_CONFIG_HOME/conda/condarc.d/',
    '~/.config/conda/.condarc',
    '~/.config/conda/condarc',
    '~/.config/conda/condarc.d/',
    '~/.conda/.condarc',
    '~/.conda/condarc',
    '~/.conda/condarc.d/',
    '~/.condarc',
    '$CONDA_PREFIX/.condarc',
    '$CONDA_PREFIX/condarc',
    '$CONDA_PREFIX/condarc.d/',
    '$CONDARC',
)

DEFAULT_CHANNEL_ALIAS = 'https://conda.anaconda.org'
CONDA_HOMEPAGE_URL = 'https://conda.io'
ERROR_UPLOAD_URL = 'https://conda.io/conda-post/unexpected-error'
DEFAULTS_CHANNEL_NAME = 'defaults'

KNOWN_SUBDIRS = PLATFORM_DIRECTORIES = (
    "noarch",
    "linux-32",
    "linux-64",
    "linux-aarch64",
    "linux-armv6l",
    "linux-armv7l",
    "linux-ppc64",
    "linux-ppc64le",
    "linux-s390x",
    "osx-64",
    "osx-arm64",
    "win-32",
    "win-64",
    "zos-z",
)

RECOGNIZED_URL_SCHEMES = ('http', 'https', 'ftp', 's3', 'file')


DEFAULT_CHANNELS_UNIX = (
    'https://repo.anaconda.com/pkgs/main',
    'https://repo.anaconda.com/pkgs/r',
)

DEFAULT_CHANNELS_WIN = (
    'https://repo.anaconda.com/pkgs/main',
    'https://repo.anaconda.com/pkgs/r',
    'https://repo.anaconda.com/pkgs/msys2',
)

DEFAULT_CUSTOM_CHANNELS = {
    'pkgs/pro': 'https://repo.anaconda.com',
}

DEFAULT_CHANNELS = DEFAULT_CHANNELS_WIN if on_win else DEFAULT_CHANNELS_UNIX

ROOT_ENV_NAME = 'base'

ROOT_NO_RM = (
    'python',
    'pycosat',
    'ruamel_yaml',
    'conda',
    'openssl',
    'requests',
)

DEFAULT_AGGRESSIVE_UPDATE_PACKAGES = (
    'ca-certificates',
    'certifi',
    'openssl',
)

if on_win:
    COMPATIBLE_SHELLS = (
        'bash',
        'cmd.exe',
        'fish',
        'tcsh',
        'xonsh',
        'zsh',
        'powershell',
    )
else:
    COMPATIBLE_SHELLS = (
        'bash',
        'fish',
        'tcsh',
        'xonsh',
        'zsh',
        'powershell',
    )


# Maximum priority, reserved for packages we really want to remove
MAX_CHANNEL_PRIORITY = 10000

CONDA_PACKAGE_EXTENSION_V1 = ".tar.bz2"
CONDA_PACKAGE_EXTENSION_V2 = ".conda"
CONDA_PACKAGE_EXTENSIONS = (
    CONDA_PACKAGE_EXTENSION_V2,
    CONDA_PACKAGE_EXTENSION_V1,
)
CONDA_TARBALL_EXTENSION = CONDA_PACKAGE_EXTENSION_V1  # legacy support for conda-build; remove this line  # NOQA
CONDA_TEMP_EXTENSION = '.c~'

UNKNOWN_CHANNEL = "<unknown>"
REPODATA_FN = 'repodata.json'


# TODO: Determine whether conda.base is the right place for this data; it
# should be a constant, but another module may be more appropriate.
#
# You could argue that the signatures being here is not necessary; indeed, we
# are not necessarily going to be able to check them *properly* (based on some
# prior expectations) as the user, since this is the beginning of trust
# bootstrapping, the first/backup version of the root of trust metadata.
# Still, the signatures here are useful for diagnostic purposes, and, more
# important, to allow self-consistency checks: that helps us avoid breaking the
# chain of trust if someone accidentally lists the wrong keys down the line. (:
# The discrepancy can be detected when loading the root data, and we can
# decline to cache incorrect trust metadata that would make further root
# updates impossible.
#
INITIAL_TRUST_ROOT = {
    "signatures": {
        "6d4d5888398ad77465e9fd53996309187723e16509144aa6733015c960378e7a": {
            "other_headers": "04001608001d162104d2ca1d4bf5d77e7c312534284dd9c45328b685ec0502605dbb03",  # noqa: E501
            "signature": "b71c9b3aa60e77258c402e574397127bcb4bc15ef3055ada8539b0d1e355bf1415a135fb7cecc9244f839a929f6b1f82844a5b3df8d6225ec9a50b181692490f"  # noqa: E501
        },
        "508debb915ede0b16dc0cff63f250bde73c5923317b44719fcfc25cc95560c44": {
            "other_headers": "04001608001d162104e6dffee4638f24cfa60a08ba03afe1314a3a38fc050260621281",  # noqa: E501
            "signature": "29d53d4e7dbea0a3efb07266d22e57cf4df7abe004453981c631245716e1b737c7a6b4ab95f42592af70be67abf56e97020e1aa1f52b49ef39b37481f05d5701"  # noqa: E501
        }
    },
    "signed": {
        "delegations": {
            "key_mgr": {
                "pubkeys": [
                    "f24c813d23a9b26be665eee5c54680c35321061b337f862385ed6d783b0bedb0"
                ],
                "threshold": 1
            },
            "root": {
                "pubkeys": [
                    "668a3217d72d4064edb16648435dc4a3e09a172ecee45dcab1464dcd2f402ec6",
                    "508debb915ede0b16dc0cff63f250bde73c5923317b44719fcfc25cc95560c44",
                    "6d4d5888398ad77465e9fd53996309187723e16509144aa6733015c960378e7a",
                    "e0c88b4c0721bd451b7e720dfb0d0bb6b3853f0cbcf5570edd73367d0841be51"
                ],
                "threshold": 2
            }
        },
        "expiration": "2022-10-31T18:00:00Z",
        "metadata_spec_version": "0.6.0",
        "timestamp": "2021-03-26T00:00:00Z",
        "type": "root",
        "version": 1
    }
}


class SafetyChecks(Enum):
    disabled = 'disabled'
    warn = 'warn'
    enabled = 'enabled'

    def __str__(self):
        return self.value


class PathConflict(Enum):
    clobber = 'clobber'
    warn = 'warn'
    prevent = 'prevent'

    def __str__(self):
        return self.value


class DepsModifier(Enum):
    """Flags to enable alternate handling of dependencies."""
    NOT_SET = 'not_set'  # default
    NO_DEPS = 'no_deps'
    ONLY_DEPS = 'only_deps'

    def __str__(self):
        return self.value


class UpdateModifier(Enum):
    SPECS_SATISFIED_SKIP_SOLVE = 'specs_satisfied_skip_solve'
    FREEZE_INSTALLED = 'freeze_installed'  # freeze is a better name for --no-update-deps
    UPDATE_DEPS = 'update_deps'
    UPDATE_SPECS = 'update_specs'  # default
    UPDATE_ALL = 'update_all'
    # TODO: add REINSTALL_ALL, see https://github.com/conda/conda/issues/6247 and https://github.com/conda/conda/issues/3149  # NOQA

    def __str__(self):
        return self.value


class ChannelPriorityMeta(EnumMeta):

    def __call__(cls, value, *args, **kwargs):
        try:
            return super(ChannelPriorityMeta, cls).__call__(value, *args, **kwargs)
        except ValueError:
            if isinstance(value, string_types):
                from ..auxlib.type_coercion import typify
                value = typify(value)
            if value is True:
                value = 'flexible'
            elif value is False:
                value = cls.DISABLED
            return super(ChannelPriorityMeta, cls).__call__(value, *args, **kwargs)


class ChannelPriority(six_with_metaclass(ChannelPriorityMeta, Enum)):
    __name__ = "ChannelPriority"

    STRICT = 'strict'
    # STRICT_OR_FLEXIBLE = 'strict_or_flexible'  # TODO: consider implementing if needed
    FLEXIBLE = 'flexible'
    DISABLED = 'disabled'

    def __str__(self):
        return self.value


class SatSolverChoice(Enum):
    PYCOSAT = 'pycosat'
    PYCRYPTOSAT = 'pycryptosat'
    PYSAT = 'pysat'

    def __str__(self):
        return self.value


class ExperimentalSolverChoice(Enum):
    CLASSIC = 'classic'
    LIBMAMBA = 'libmamba'
    LIBMAMBA_DRAFT = 'libmamba-draft'

    def __str__(self):
        return self.value


# Magic files for permissions determination
PACKAGE_CACHE_MAGIC_FILE = 'urls.txt'
PREFIX_MAGIC_FILE = join('conda-meta', 'history')

PREFIX_STATE_FILE = join('conda-meta', 'state')
PACKAGE_ENV_VARS_DIR = join('etc', 'conda', 'env_vars.d')
CONDA_ENV_VARS_UNSET_VAR = "***unset***"


# TODO: should be frozendict(), but I don't want to import frozendict from auxlib here.
NAMESPACES_MAP = {  # base package name, namespace
    "python": "python",
    "r": "r",
    "r-base": "r",
    "mro-base": "r",
    "erlang": "erlang",
    "java": "java",
    "openjdk": "java",
    "julia": "julia",
    "latex": "latex",
    "lua": "lua",
    "nodejs": "js",
    "perl": "perl",
    "php": "php",
    "ruby": "ruby",
    "m2-base": "m2",
    "msys2-conda-epoch": "m2w64",
}

NAMESPACE_PACKAGE_NAMES = frozenset(NAMESPACES_MAP)
NAMESPACES = frozenset(itervalues(NAMESPACES_MAP))

# Namespace arbiters of uniqueness
#  global: some repository established by Anaconda, Inc. and conda-forge
#  python: https://pypi.org/simple
#  r: https://cran.r-project.org/web/packages/available_packages_by_name.html
#  erlang: https://hex.pm/packages
#  java: https://repo1.maven.org/maven2/
#  julia: https://pkg.julialang.org/
#  latex: https://ctan.org/pkg
#  lua: https://luarocks.org/m/root
#  js: https://docs.npmjs.com/misc/registry
#  pascal: ???
#  perl: https://www.cpan.org/modules/01modules.index.html
#  php: https://packagist.org/
#  ruby: https://rubygems.org/gems
#  clojure: https://clojars.org/


# Not all python namespace packages are registered on PyPI. If a package
# contains files in site-packages, it probably belongs in the python namespace.
