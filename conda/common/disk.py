# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
from os import makedirs
from os.path import isdir

log = getLogger(__name__)


def conda_bld_ensure_dir(path):
    # this can fail in parallel operation, depending on timing.  Just try to make the dir,
    #    but don't bail if fail.
    if not isdir(path):
        try:
            makedirs(path)
        except OSError:
            pass
