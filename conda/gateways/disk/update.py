# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals


class CancelOperation(Exception):
    pass


def update_file_as_binary(file_full_path, callback):
    # callback should be a callable that takes one positional argument, which is the
    # content of the file before updating
    with open(file_full_path, 'rb') as fh:
        data = fh.read()
        fh.seek(0)
        try:
            fh.write(callback(data))
            fh.truncate()
        except CancelOperation:
            pass  # NOQA
