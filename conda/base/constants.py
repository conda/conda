# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
This file should hold most string literals and magic numbers used throughout the code base.
The exception is if a literal is specifically meant to be private to and isolated within a module.
Think of this as a "more static" source of configuration information.

Another important source of "static" configuration is conda/models/enums.py.
"""

import struct
from enum import Enum, EnumMeta
from os.path import join

from ..common.compat import on_win

PREFIX_PLACEHOLDER: str = (
    "/opt/anaconda1anaconda2"
    # this is intentionally split into parts, such that running
    # this program on itself will leave it unchanged
    "anaconda3"
)

machine_bits: int = 8 * struct.calcsize("P")

APP_NAME: str = "conda"

SEARCH_PATH: tuple[str]

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

DEFAULT_CHANNEL_ALIAS: str = "https://conda.anaconda.org"
CONDA_HOMEPAGE_URL: str = "https://conda.io"
ERROR_UPLOAD_URL: str = "https://conda.io/conda-post/unexpected-error"
DEFAULTS_CHANNEL_NAME: str = "defaults"

KNOWN_SUBDIRS: tuple[str]
PLATFORM_DIRECTORIES: tuple[str]

KNOWN_SUBDIRS = PLATFORM_DIRECTORIES = (
    "noarch",
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

RECOGNIZED_URL_SCHEMES: tuple[str] = ("http", "https", "ftp", "s3", "file")


DEFAULT_CHANNELS_UNIX: tuple[str] = (
    "https://repo.anaconda.com/pkgs/main",
    "https://repo.anaconda.com/pkgs/r",
)

DEFAULT_CHANNELS_WIN: tuple[str] = (
    "https://repo.anaconda.com/pkgs/main",
    "https://repo.anaconda.com/pkgs/r",
    "https://repo.anaconda.com/pkgs/msys2",
)

DEFAULT_CUSTOM_CHANNELS: tuple[str] = {
    "pkgs/pro": "https://repo.anaconda.com",
}

DEFAULT_CHANNELS: tuple[str] = DEFAULT_CHANNELS_WIN if on_win else DEFAULT_CHANNELS_UNIX

ROOT_ENV_NAME: str = "base"
UNUSED_ENV_NAME: str = "unused-env-name"

ROOT_NO_RM: tuple[str] = (
    "python",
    "pycosat",
    "ruamel.yaml",
    "conda",
    "openssl",
    "requests",
)

DEFAULT_AGGRESSIVE_UPDATE_PACKAGES: tuple[str] = (
    "ca-certificates",
    "certifi",
    "openssl",
)

COMPATIBLE_SHELLS: tuple[str]

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
MAX_CHANNEL_PRIORITY: int = 10000

CONDA_PACKAGE_EXTENSION_V1: str = ".tar.bz2"
CONDA_PACKAGE_EXTENSION_V2: str = ".conda"
CONDA_PACKAGE_EXTENSIONS: tuple[str] = (
    CONDA_PACKAGE_EXTENSION_V2,
    CONDA_PACKAGE_EXTENSION_V1,
)
CONDA_PACKAGE_PARTS: tuple[str] = tuple(
    f"{ext}.part" for ext in CONDA_PACKAGE_EXTENSIONS
)
CONDA_TARBALL_EXTENSION: str = (
    CONDA_PACKAGE_EXTENSION_V1  # legacy support for conda-build
)
CONDA_TEMP_EXTENSION: str = ".c~"
CONDA_TEMP_EXTENSIONS: tuple[str] = (CONDA_TEMP_EXTENSION, ".trash")
CONDA_LOGS_DIR: str = ".logs"

UNKNOWN_CHANNEL: str = "<unknown>"
REPODATA_FN: str = "repodata.json"

#: Default name of the notices file on the server we look for
NOTICES_FN: str = "notices.json"

#: Name of cache file where read notice IDs are stored
NOTICES_CACHE_FN: str = "notices.cache"

#: Determines the subdir for notices cache
NOTICES_CACHE_SUBDIR: str = "notices"

#: Determines the subdir for notices cache
NOTICES_DECORATOR_DISPLAY_INTERVAL: int = 86400  # in seconds

DRY_RUN_PREFIX: str = "Dry run action:"
PREFIX_NAME_DISALLOWED_CHARS: set[str] = {"/", " ", ":", "#"}


class SafetyChecks(Enum):
    disabled = "disabled"
    warn = "warn"
    enabled = "enabled"

    def __str__(self):
        return self.value


class PathConflict(Enum):
    clobber = "clobber"
    warn = "warn"
    prevent = "prevent"

    def __str__(self):
        return self.value


class DepsModifier(Enum):
    """Flags to enable alternate handling of dependencies."""

    NOT_SET = "not_set"  # default
    NO_DEPS = "no_deps"
    ONLY_DEPS = "only_deps"

    def __str__(self):
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

    def __str__(self):
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

    def __str__(self):
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
DEFAULT_SOLVER: str = "libmamba"
CLASSIC_SOLVER: str = "classic"

#: The name of the default json reporter backend
DEFAULT_JSON_REPORTER_BACKEND = "json"

#: The name of the default console reporter backend
DEFAULT_CONSOLE_REPORTER_BACKEND = "classic"


class NoticeLevel(ValueEnum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


# Magic files for permissions determination
PACKAGE_CACHE_MAGIC_FILE: str = "urls.txt"
PREFIX_MAGIC_FILE: str = join("conda-meta", "history")

PREFIX_STATE_FILE: str = join("conda-meta", "state")
PACKAGE_ENV_VARS_DIR: str = join("etc", "conda", "env_vars.d")
CONDA_ENV_VARS_UNSET_VAR: str = "***unset***"


# TODO: should be frozendict(), but I don't want to import frozendict from auxlib here.
NAMESPACES_MAP: dict[str, str] = {  # base package name, namespace
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

NAMESPACE_PACKAGE_NAMES: frozenset[str] = frozenset(NAMESPACES_MAP)
NAMESPACES: frozenset[str] = frozenset(NAMESPACES_MAP.values())

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
NO_PLUGINS: bool = False
