# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from platform import machine
import sys

from enum import Enum

from .._vendor.auxlib.ish import dals
from .._vendor.auxlib.type_coercion import TypeCoercionError, boolify
from ..common.compat import string_types
from ..exceptions import CondaUpgradeError


class Arch(Enum):
    x86 = 'x86'
    x86_64 = 'x86_64'
    armv6l = 'armv6l'
    armv7l = 'armv7l'
    ppc64le = 'ppc64le'
    z = 'z'

    @classmethod
    def from_sys(cls):
        if sys.platform == 'zos':
            return cls['z']
        return cls[machine()]

    def __json__(self):
        return self.value


class Platform(Enum):
    linux = 'linux'
    win = 'win32'
    openbsd = 'openbsd5'
    osx = 'darwin'
    zos = 'zos'

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


class FileMode(Enum):
    text = 'text'
    binary = 'binary'

    def __str__(self):
        return "%s" % self.value


class LinkType(Enum):
    # directory is not a link type, and copy is not a path type
    # LinkType is still probably the best name here
    hardlink = 1
    softlink = 2
    copy = 3
    directory = 4

    def __int__(self):
        return self.value

    def __str__(self):
        return self.name

    def __json__(self):
        return self.name


class PathType(Enum):
    """
    Refers to if the file in question is hard linked or soft linked. Originally designed to be used
    in paths.json
    """
    hardlink = 'hardlink'
    softlink = 'softlink'
    directory = 'directory'

    # these additional types should not be included by conda-build in packages
    linked_package_record = 'linked_package_record'  # a package's .json file in conda-meta
    pyc_file = 'pyc_file'
    unix_python_entry_point = 'unix_python_entry_point'
    windows_python_entry_point = 'windows_python_entry_point'

    def __str__(self):
        return self.name

    def __json__(self):
        return self.name


class NoarchType(Enum):
    generic = 'generic'
    python = 'python'

    @staticmethod
    def coerce(val):
        # what a mess
        if isinstance(val, NoarchType):
            return val
        if isinstance(val, bool):
            val = NoarchType.generic if val else None
        if isinstance(val, string_types):
            val = val.lower()
            if val == 'python':
                val = NoarchType.python
            elif val == 'generic':
                val = NoarchType.generic
            else:
                try:
                    val = NoarchType.generic if boolify(val) else None
                except TypeCoercionError:
                    raise CondaUpgradeError(dals("""
                    The noarch type for this package is set to '%s'.
                    The current version of conda is too old to install this package.
                    Please update conda.
                    """ % val))
        return val
