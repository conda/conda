# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Implements object describing a symbolic link from the base environment to a private environment.

Since private environments are an unrealized feature of conda and has been deprecated this data
model no longer serves a purpose and has also been deprecated.
"""
from logging import getLogger

from ..auxlib.entity import Entity, EnumField, StringField
from ..deprecations import deprecated
from .enums import LeasedPathType

log = getLogger(__name__)


@deprecated("24.3", "24.9")
class LeasedPathEntry(Entity):
    """
    _path: short path for the leased path, using forward slashes
    target_path: the full path to the executable in the private env
    target_prefix: the full path to the private environment
    leased_path: the full path for the lease in the root prefix
    package_name: the package holding the lease
    leased_path_type: application_entry_point

    """

    _path = StringField()
    target_path = StringField()
    target_prefix = StringField()
    leased_path = StringField()
    package_name = StringField()
    leased_path_type = EnumField(LeasedPathType)
