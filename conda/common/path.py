# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from functools import reduce
from logging import getLogger

log = getLogger(__name__)


def tokenized_startswith(test_iterable, startswith_iterable):
    return all(t == sw for t, sw in zip(test_iterable, startswith_iterable))


def get_leaf_directories(files):
    # type: (List[str]) -> List[str]
    # give this function a list of files, and it will hand back a list of leaf directories to
    # pass to os.makedirs()
    directories = sorted(set(tuple(f.split('/')[:-1]) for f in files))
    if not directories:
        return ()

    leaves = []

    def _process(x, y):
        if not tokenized_startswith(y, x):
            leaves.append(x)
        return y
    last = reduce(_process, directories)

    if not leaves:
        leaves.append(directories[-1])
    elif not tokenized_startswith(last, leaves[-1]):
        leaves.append(last)

    return tuple('/'.join(leaf) for leaf in leaves)
