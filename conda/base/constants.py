# -*- coding: utf-8 -*-
"""
This file should hold almost all string literals and magic numbers used throughout the code base.
The exception is if a literal is specifically meant to be private to and isolated within a module.
"""
from __future__ import absolute_import, division, print_function

import sys
from enum import Enum
from logging import getLogger
from platform import machine

from .._vendor.auxlib.collection import frozendict

log = getLogger(__name__)


class Arch(Enum):
    x86 = 'x86'
    x86_64 = 'x86_64'
    armv6l = 'armv6l'
    armv7l = 'armv7l'
    ppc64le = 'ppc64le'

    @classmethod
    def from_sys(cls):
        return cls[machine()]

    def __json__(self):
        return self.value


class Platform(Enum):
    linux = 'linux'
    win = 'win32'
    openbsd = 'openbsd5'
    osx = 'darwin'

    @classmethod
    def from_sys(cls):
        p = sys.platform
        if p.startswith('linux'):
            # Changed in version 2.7.3: Since lots of code check for sys.platform == 'linux2',
            # and there is no essential change between Linux 2.x and 3.x, sys.platform is always
            # set to 'linux2', even on Linux 3.x. In Python 3.3 and later, the value will always
            # be set to 'linux'
            p = 'linux'
        return cls(p)

    def __json__(self):
        return self.value


machine_bits = 8 * tuple.__itemsize__

CONDA = 'CONDA'
CONDA_ = 'CONDA_'
conda = 'conda'

SEARCH_PATH = (
    '/etc/conda/condarc',
    '/etc/conda/condarc.d/',
    '/var/lib/conda/condarc',
    '/var/lib/conda/condarc.d/',
    '$CONDA_ROOT/condarc',
    '$CONDA_ROOT/.condarc',
    '$CONDA_ROOT/condarc.d/',
    '~/.conda/condarc',
    '~/.conda/condarc.d/',
    '~/.condarc',
    '$CONDA_PREFIX/.condarc',
    '$CONDA_PREFIX/condarc.d/',
    '$CONDARC',
)

DEFAULT_CHANNEL_ALIAS = 'https://conda.anaconda.org'
CONDA_HOMEPAGE_URL = 'http://conda.pydata.org'

PLATFORM_DIRECTORIES = ("linux-64",
                        "linux-32",
                        "win-64",
                        "win-32",
                        "osx-64",
                        "linux-ppc64le",
                        "noarch",
                        )

RECOGNIZED_URL_SCHEMES = ('http', 'https', 'ftp', 's3', 'file')

DEFAULT_CHANNELS_UNIX = ('https://repo.continuum.io/pkgs/free',
                         'https://repo.continuum.io/pkgs/pro',
                         )

DEFAULT_CHANNELS_WIN = ('https://repo.continuum.io/pkgs/free',
                        'https://repo.continuum.io/pkgs/pro',
                        'https://repo.continuum.io/pkgs/msys2',
                        )

if Platform.from_sys() is Platform.win:
    DEFAULT_CHANNELS = DEFAULT_CHANNELS_WIN
else:
    DEFAULT_CHANNELS = DEFAULT_CHANNELS_UNIX

ROOT_ENV_NAME = 'root'

EMPTY_MAP = frozendict()


class _Null(object):
    def __nonzero__(self):
        return False

    def __bool__(self):
        return False

    def __len__(self):
        return 0


NULL = _Null()

UTF8 = 'UTF-8'
