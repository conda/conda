# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from os.path import split

from functools import reduce
from logging import getLogger

log = getLogger(__name__)


files = """
bin/django-admin
bin/django-admin.py
lib/python3.5/site-packages/Django-1.10.2-py3.5.egg-info/PKG-INFO
lib/python3.5/site-packages/Django-1.10.2-py3.5.egg-info/SOURCES.txt
lib/python3.5/site-packages/Django-1.10.2-py3.5.egg-info/dependency_links.txt
lib/python3.5/site-packages/Django-1.10.2-py3.5.egg-info/entry_points.txt
lib/python3.5/site-packages/Django-1.10.2-py3.5.egg-info/not-zip-safe
lib/python3.5/site-packages/Django-1.10.2-py3.5.egg-info/requires.txt
lib/python3.5/site-packages/Django-1.10.2-py3.5.egg-info/scripts/django-admin.py
lib/python3.5/site-packages/Django-1.10.2-py3.5.egg-info/top_level.txt
lib/python3.5/site-packages/django/__init__.py
lib/python3.5/site-packages/django/__main__.py
lib/python3.5/site-packages/django/__pycache__/__init__.cpython-35.pyc
lib/python3.5/site-packages/django/__pycache__/__main__.cpython-35.pyc
lib/python3.5/site-packages/django/__pycache__/shortcuts.cpython-35.pyc
lib/python3.5/site-packages/django/apps/__init__.py
lib/python3.5/site-packages/django/apps/__pycache__/__init__.cpython-35.pyc
lib/python3.5/site-packages/django/apps/__pycache__/config.cpython-35.pyc
lib/python3.5/site-packages/django/apps/__pycache__/registry.cpython-35.pyc
lib/python3.5/site-packages/django/apps/config.py
lib/python3.5/site-packages/django/apps/registry.py
"""


def tokenized_startswith(test_iterable, startswith_iterable):
    return all(t == sw for t, sw in zip(test_iterable, startswith_iterable))


def get_leaf_directories(files):
    # type: (List[str]) -> List[str]
    # give this function a list of files, and it will hand back a list of leaf directories to
    # pass to os.makedirs()
    files = files.strip().split('\n')

    directories = sorted(set(tuple(f.split('/')[:-1]) for f in files))
    leaves = []

    def _process(x, y):
        if not tokenized_startswith(y, x):
            leaves.append(x)
        return y

    last = reduce(_process, directories)
    if not tokenized_startswith(last, leaves[-1]):
        leaves.append(last)

    return leaves
