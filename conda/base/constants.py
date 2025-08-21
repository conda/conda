# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
This file should hold most string literals and magic numbers used throughout the code base.
The exception is if a literal is specifically meant to be private to and isolated within a module.
Think of this as a "more static" source of configuration information.

Another important source of "static" configuration is conda/models/enums.py.
"""

from __future__ import annotations

import struct
from enum import Enum, EnumMeta
from os.path import join
from typing import TYPE_CHECKING

from ..common.compat import on_win

if TYPE_CHECKING:
    from typing import Final

    from ..common.path import PathType

PREFIX_PLACEHOLDER: Final = (
    "/opt/anaconda1anaconda2"
    # this is intentionally split into parts, such that running
    # this program on itself will leave it unchanged
    "anaconda3"
)

machine_bits: Final = 8 * struct.calcsize("P")

APP_NAME: Final = "conda"

SEARCH_PATH: tuple[str, ...]

if on_win:  # pragma: no cover
    SEARCH_PATH = (
        "C:/ProgramData/conda/.condarc",
        "C:/ProgramData/conda/condarc",
        "C:/ProgramData/conda/condarc.d",
    )
else:
    SEARCH_PATH = (
        "/etc/conda/.condarc",
        "/etc/conda/condarc",
        "/etc/conda/condarc.d/",
        "/var/lib/conda/.condarc",
        "/var/lib/conda/condarc",
        "/var/lib/conda/condarc.d/",
    )

SEARCH_PATH += (
    "$CONDA_ROOT/.condarc",
    "$CONDA_ROOT/condarc",
    "$CONDA_ROOT/condarc.d/",
    "$XDG_CONFIG_HOME/conda/.condarc",
    "$XDG_CONFIG_HOME/conda/condarc",
    "$XDG_CONFIG_HOME/conda/condarc.d/",
    "~/.config/conda/.condarc",
    "~/.config/conda/condarc",
    "~/.config/conda/condarc.d/",
    "~/.conda/.condarc",
    "~/.conda/condarc",
    "~/.conda/condarc.d/",
    "~/.condarc",
    "$CONDA_PREFIX/.condarc",
    "$CONDA_PREFIX/condarc",
    "$CONDA_PREFIX/condarc.d/",
    "$CONDARC",
)

DEFAULT_CHANNEL_ALIAS: Final = "https://conda.anaconda.org"
CONDA_HOMEPAGE_URL: Final = "https://conda.io"
ERROR_UPLOAD_URL: Final = "https://conda.io/conda-post/unexpected-error"
DEFAULTS_CHANNEL_NAME: Final = "defaults"

PLATFORMS: Final = (
    "emscripten-wasm32",
    "wasi-wasm32",
    "freebsd-64",
    "linux-32",
    "linux-64",
    "linux-aarch64",
    "linux-armv6l",
    "linux-armv7l",
    "linux-ppc64",
    "linux-ppc64le",
    "linux-riscv64",
    "linux-s390x",
    "osx-64",
    "osx-arm64",
    "win-32",
    "win-64",
    "win-arm64",
    "zos-z",
)
KNOWN_SUBDIRS: Final = ("noarch", *PLATFORMS)
PLATFORM_DIRECTORIES = KNOWN_SUBDIRS

RECOGNIZED_URL_SCHEMES: Final = ("http", "https", "ftp", "s3", "file")


DEFAULT_CHANNELS_UNIX: Final = (
    "https://repo.anaconda.com/pkgs/main",
    "https://repo.anaconda.com/pkgs/r",
)

DEFAULT_CHANNELS_WIN: Final = (
    "https://repo.anaconda.com/pkgs/main",
    "https://repo.anaconda.com/pkgs/r",
    "https://repo.anaconda.com/pkgs/msys2",
)

DEFAULT_CUSTOM_CHANNELS: Final = {
    "pkgs/pro": "https://repo.anaconda.com",
}

DEFAULT_CHANNELS: Final = DEFAULT_CHANNELS_WIN if on_win else DEFAULT_CHANNELS_UNIX

ROOT_ENV_NAME: Final = "base"
RESERVED_ENV_NAMES: Final = (
    ROOT_ENV_NAME,
    "root",
)
UNUSED_ENV_NAME: Final = "unused-env-name"

ROOT_NO_RM: Final = (
    "python",
    "pycosat",
    "ruamel.yaml",
    "conda",
    "openssl",
    "requests",
)

DEFAULT_AGGRESSIVE_UPDATE_PACKAGES: Final = (
    "ca-certificates",
    "certifi",
    "openssl",
)

COMPATIBLE_SHELLS: tuple[str, ...]

if on_win:  # pragma: no cover
    COMPATIBLE_SHELLS = (
        "bash",
        "cmd.exe",
        "fish",
        "tcsh",
        "xonsh",
        "zsh",
        "powershell",
    )
else:
    COMPATIBLE_SHELLS = (
        "bash",
        "fish",
        "tcsh",
        "xonsh",
        "zsh",
        "powershell",
    )


# Maximum priority, reserved for packages we really want to remove
MAX_CHANNEL_PRIORITY: Final = 10000

CONDA_PACKAGE_EXTENSION_V1: Final = ".tar.bz2"
CONDA_PACKAGE_EXTENSION_V2: Final = ".conda"
CONDA_PACKAGE_EXTENSIONS: Final = (
    CONDA_PACKAGE_EXTENSION_V2,
    CONDA_PACKAGE_EXTENSION_V1,
)
CONDA_PACKAGE_PARTS: Final = tuple(f"{ext}.part" for ext in CONDA_PACKAGE_EXTENSIONS)
CONDA_TARBALL_EXTENSION: Final = (
    CONDA_PACKAGE_EXTENSION_V1  # legacy support for conda-build
)
CONDA_TEMP_EXTENSION: Final = ".c~"
CONDA_TEMP_EXTENSIONS: Final = (CONDA_TEMP_EXTENSION, ".trash")
CONDA_LOGS_DIR: Final = ".logs"

UNKNOWN_CHANNEL: Final = "<unknown>"
REPODATA_FN: Final = "repodata.json"

#: Default name of the notices file on the server we look for
NOTICES_FN: Final = "notices.json"

#: Name of cache file where read notice IDs are stored
NOTICES_CACHE_FN: Final = "notices.cache"

#: Determines the subdir for notices cache
NOTICES_CACHE_SUBDIR: Final = "notices"

#: Determines how often notices are displayed while running commands
NOTICES_DECORATOR_DISPLAY_INTERVAL: Final = 86400  # in seconds

DRY_RUN_PREFIX: Final = "Dry run action:"
PREFIX_NAME_DISALLOWED_CHARS: Final = {"/", " ", ":", "#"}


class SafetyChecks(Enum):
    disabled = "disabled"
    warn = "warn"
    enabled = "enabled"

    def __str__(self) -> str:
        return self.value


class PathConflict(Enum):
    clobber = "clobber"
    warn = "warn"
    prevent = "prevent"

    def __str__(self) -> str:
        return self.value


class DepsModifier(Enum):
    """Flags to enable alternate handling of dependencies."""

    NOT_SET = "not_set"  # default
    NO_DEPS = "no_deps"
    ONLY_DEPS = "only_deps"

    def __str__(self) -> str:
        return self.value


class UpdateModifier(Enum):
    SPECS_SATISFIED_SKIP_SOLVE = "specs_satisfied_skip_solve"
    FREEZE_INSTALLED = (
        "freeze_installed"  # freeze is a better name for --no-update-deps
    )
    UPDATE_DEPS = "update_deps"
    UPDATE_SPECS = "update_specs"  # default
    UPDATE_ALL = "update_all"
    # TODO: add REINSTALL_ALL, see https://github.com/conda/conda/issues/6247 and https://github.com/conda/conda/issues/3149

    def __str__(self) -> str:
        return self.value


class ChannelPriorityMeta(EnumMeta):
    def __call__(cls, value, *args, **kwargs):
        try:
            return super().__call__(value, *args, **kwargs)
        except ValueError:
            if isinstance(value, str):
                from ..auxlib.type_coercion import typify

                value = typify(value)
            if value is True:
                value = "flexible"
            elif value is False:
                value = cls.DISABLED
            return super().__call__(value, *args, **kwargs)


class ValueEnum(Enum):
    """Subclass of enum that returns the value of the enum as its str representation"""

    def __str__(self) -> str:
        return f"{self.value}"


class ChannelPriority(ValueEnum, metaclass=ChannelPriorityMeta):
    __name__ = "ChannelPriority"

    STRICT = "strict"
    # STRICT_OR_FLEXIBLE = 'strict_or_flexible'  # TODO: consider implementing if needed
    FLEXIBLE = "flexible"
    DISABLED = "disabled"


class SatSolverChoice(ValueEnum):
    PYCOSAT = "pycosat"
    PYCRYPTOSAT = "pycryptosat"
    PYSAT = "pysat"


#: The name of the default solver, currently "libmamba"
DEFAULT_SOLVER: Final = "libmamba"
CLASSIC_SOLVER: Final = "classic"

#: The name of the default json reporter backend
DEFAULT_JSON_REPORTER_BACKEND: Final = "json"

#: The name of the default console reporter backend
DEFAULT_CONSOLE_REPORTER_BACKEND: Final = "classic"

#: The default `conda list` columns
DEFAULT_CONDA_LIST_FIELDS: Final = ("name", "version", "build", "channel_name")
CONDA_LIST_FIELDS: Final = {
    # Keys MUST be valid attributes in conda.core.records.PrefixRecords
    # Values are the displayed column title
    "arch": "Arch",
    "build": "Build",
    "build_number": "Build number",
    "channel": "Channel URL",
    "channel_name": "Channel",
    "constrains": "Constraints",
    "depends": "Dependencies",
    "dist_str": "Dist",
    "features": "Features",
    "fn": "Filename",
    "license": "License",
    "license_family": "License family",
    "md5": "MD5",
    "name": "Name",
    "noarch": "Noarch",
    "package_type": "Package type",
    "requested_spec": "Requested",
    "sha256": "SHA256",
    "size": "Size",
    "subdir": "Subdir",
    "timestamp": "Timestamp",
    "track_features": "Track features",
    "url": "URL",
    "version": "Version",
}


class NoticeLevel(ValueEnum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


# Magic files for permissions determination
PACKAGE_CACHE_MAGIC_FILE: Final[PathType] = "urls.txt"
PREFIX_MAGIC_FILE: Final[PathType] = join("conda-meta", "history")
PREFIX_FROZEN_FILE: Final[PathType] = join("conda-meta", "frozen")

PREFIX_STATE_FILE: Final[PathType] = join("conda-meta", "state")
PREFIX_PINNED_FILE: Final[PathType] = join("conda-meta", "pinned")
PACKAGE_ENV_VARS_DIR: Final[PathType] = join("etc", "conda", "env_vars.d")
CONDA_ENV_VARS_UNSET_VAR: Final = "***unset***"


# TODO: should be frozendict(), but I don't want to import frozendict from auxlib here.
NAMESPACES_MAP: Final = {  # base package name, namespace
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

NAMESPACE_PACKAGE_NAMES: Final = frozenset(NAMESPACES_MAP)
NAMESPACES: Final = frozenset(NAMESPACES_MAP.values())

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


# Indicates whether or not external plugins (i.e., plugins that aren't shipped
# with conda) are enabled
NO_PLUGINS: Final = False

# When this string is present in an environment file, it indicates that the file
# describes an explicit environment spec.
EXPLICIT_MARKER: Final = "@EXPLICIT"

# These variables describe the various sources for config that are supported by conda.
# In addition to these sources, conda also supports configuration from condarc config
# files (these are referred to in the context object by their full path as a pathlib.Path).
CMD_LINE_SOURCE: Final = "cmd_line"
ENV_VARS_SOURCE: Final = "envvars"
CONFIGURATION_SOURCES: Final = (CMD_LINE_SOURCE, ENV_VARS_SOURCE)
