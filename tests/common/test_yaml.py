# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger

from conda.auxlib.ish import dals
from conda.common.serialize import yaml_round_trip_dump, yaml_round_trip_load

log = getLogger(__name__)


def test_dump():
    obj = dict([
        ('a_seq', [1, 2, 3]),
        ('a_map', {'a_key': 'a_value'}),
    ])
    assert obj == yaml_round_trip_load(yaml_round_trip_dump(obj))


def test_seq_simple():
    test_string = dals("""
    a_seq:
      - 1
      - 2
      - 3
    """)
    assert test_string == yaml_round_trip_dump({'a_seq': [1, 2, 3]})


def test_yaml_complex():
    test_string = dals("""
    single_bool: false
    single_str: no

    # comment here
    a_seq_1:
      - 1
      - 2
      - 3

    a_seq_2:
      - 1  # with comment
      - two: 2
      - 3

    a_map:
      # comment
      field1: true
      field2: yes

    # final comment
    """)

    python_structure = {
        'single_bool': False,
        'single_str': 'no',
        'a_seq_1': [
            1,
            2,
            3,
        ],
        'a_seq_2': [
            1,
            {'two': 2},
            3,
        ],
        'a_map': {
            'field1': True,
            'field2': 'yes',
        },
    }

    loaded_from_string = yaml_round_trip_load(test_string)
    assert python_structure == loaded_from_string

    dumped_from_load = yaml_round_trip_dump(loaded_from_string)
    print(dumped_from_load)
    assert dumped_from_load == test_string


def test_map():
    test_string = dals("""
    a_map:
      a_key: a_value
    """)
    assert test_string == yaml_round_trip_dump({'a_map': {'a_key': 'a_value'}})
