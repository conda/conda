# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from contextlib import contextmanager
from os import makedirs, unlink
from os.path import isdir
from tempfile import NamedTemporaryFile


def conda_bld_ensure_dir(path):
    # this can fail in parallel operation, depending on timing.  Just try to make the dir,
    #    but don't bail if fail.
    if not isdir(path):
        try:
            makedirs(path)
        except OSError:
            pass


@contextmanager
def temporary_content_in_file(content, suffix=""):
    # content returns temporary file path with contents
    fh = None
    path = None
    try:
        fh = NamedTemporaryFile(mode="w", delete=False, suffix=suffix)
        path = fh.name
        fh.write(content)
        fh.flush()
        fh.close()
        yield path
    finally:
        if fh is not None:
            fh.close()
        if path is not None:
            unlink(path)
