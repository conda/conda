# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger

from ..os.linux import linux_get_libc_version
from ..os.unix import get_free_space_on_unix, is_admin_on_unix
from ..os.windows import get_free_space_on_windows, is_admin_on_windows
from ..compat import on_win


log = getLogger(__name__)


linux_get_libc_version


def is_admin():
    func = is_admin_on_windows if on_win else is_admin_on_unix
    return func()


def get_free_space(dir_name):
    """Return folder/drive free space (in bytes).
    :param dir_name: the dir name need to check
    :return: amount of free space

    Examples:
        >>> import os
        >>> get_free_space(os.getcwd()) > 0
        True
    """
    func = get_free_space_on_windows if on_win else get_free_space_on_unix
    return func(dir_name)
