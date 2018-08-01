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

from enum import Enum
from os.path import join

from ..common.compat import itervalues, on_win

PREFIX_PLACEHOLDER = ('/opt/anaconda1anaconda2'
                      # this is intentionally split into parts, such that running
                      # this program on itself will leave it unchanged
                      'anaconda3')

machine_bits = 8 * tuple.__itemsize__

APP_NAME = 'conda'

SEARCH_PATH = (
    '/etc/conda/.condarc',
    '/etc/conda/condarc',
    '/etc/conda/condarc.d/',
    '/var/lib/conda/.condarc',
    '/var/lib/conda/condarc',
    '/var/lib/conda/condarc.d/',
    '$CONDA_ROOT/.condarc',
    '$CONDA_ROOT/condarc',
    '$CONDA_ROOT/condarc.d/',
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

PLATFORM_DIRECTORIES = (
    "noarch",
    "linux-32",
    "linux-64",
    "linux-aarch64",
    "linux-armv6l",
    "linux-armv7l",
    "linux-ppc64le",
    "osx-64",
    "win-32",
    "win-64",
    "zos-z",
)

RECOGNIZED_URL_SCHEMES = ('http', 'https', 'ftp', 's3', 'file')


DEFAULT_CHANNELS_UNIX = (
    'https://repo.anaconda.com/pkgs/main',
    'https://repo.anaconda.com/pkgs/free',
    'https://repo.anaconda.com/pkgs/r',
)

DEFAULT_CHANNELS_WIN = (
    'https://repo.anaconda.com/pkgs/main',
    'https://repo.anaconda.com/pkgs/free',
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
    )
else:
    COMPATIBLE_SHELLS = (
        'bash',
        'fish',
        'tcsh',
        'xonsh',
        'zsh',
    )


# Maximum priority, reserved for packages we really want to remove
MAX_CHANNEL_PRIORITY = 10000

CONDA_TARBALL_EXTENSION = '.tar.bz2'

UNKNOWN_CHANNEL = "<unknown>"


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


# Magic files for permissions determination
PACKAGE_CACHE_MAGIC_FILE = 'urls.txt'
PREFIX_MAGIC_FILE = join('conda-meta', 'history')


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
