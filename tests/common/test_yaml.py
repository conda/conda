# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger

from conda._vendor.auxlib.ish import dals
from conda.common.yaml import yaml_dump, yaml_load

log = getLogger(__name__)


def test_dump():
    obj = dict([
        ('a_seq', [1, 2, 3]),
        ('a_map', {'a_key': 'a_value'}),
    ])
    assert obj == yaml_load(yaml_dump(obj))


def test_seq():
    test_string = dals("""
    a_seq:
      - 1
      - 2
      - 3
    """)
    assert test_string == yaml_dump({'a_seq': [1, 2, 3]})


def test_map():
    test_string = dals("""
    a_map:
      a_key: a_value
    """)
    assert test_string == yaml_dump({'a_map': {'a_key': 'a_value'}})
