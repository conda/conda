# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from . import exp_backoff_fn


class CancelOperation(Exception):
    pass


def update_file_as_binary(file_full_path, callback):
    # callback should be a callable that takes one positional argument, which is the
    # content of the file before updating
    fh = None
    try:
        fh = exp_backoff_fn(open, file_full_path, 'rb+')
        data = fh.read()
        fh.seek(0)
        try:
            fh.write(callback(data))
            fh.truncate()
        except CancelOperation:
            pass  # NOQA
    finally:
        if fh:
            fh.close()
