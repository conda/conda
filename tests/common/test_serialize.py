# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

import pytest

from conda.base.constants import SafetyChecks
from conda.common.serialize import (
    json,
    json_dump,
    json_load,
    yaml,
    yaml_round_trip_dump,
    yaml_round_trip_load,
)

if TYPE_CHECKING:
    from typing import Any, Callable


OBJ1 = {
    "a_seq": [1, 2, 3],
    "a_map": {"a_key": "a_value"},
}
JSON1 = """
{
  "a_map": {
    "a_key": "a_value"
  },
  "a_seq": [
    1,
    2,
    3
  ]
}
""".strip()
YAML1 = """
a_seq:
  - 1
  - 2
  - 3
a_map:
  a_key: a_value
""".lstrip()

OBJ2 = {
    "single_bool": False,
    "single_str": "no",
    "a_seq_1": [
        1,
        2,
        3,
    ],
    "a_seq_2": [
        1,
        {"two": 2},
        3,
    ],
    "a_map": {
        "field1": True,
        "field2": "yes",
    },
}
JSON2 = """
{
  "a_map": {
    "field1": true,
    "field2": "yes"
  },
  "a_seq_1": [
    1,
    2,
    3
  ],
  "a_seq_2": [
    1,
    {
      "two": 2
    },
    3
  ],
  "single_bool": false,
  "single_str": "no"
}
""".strip()
YAML2 = """
single_bool: false
single_str: no
a_seq_1:
  - 1
  - 2
  - 3
a_seq_2:
  - 1
  - two: 2
  - 3
a_map:
  field1: true
  field2: yes
""".lstrip()


@pytest.mark.parametrize(
    "obj,text,read,write,legacy_load,legacy_dump",
    [
        (
            OBJ1,
            JSON1,
            json.read,
            partial(json.write, sort_keys=True),
            json_load,
            json_dump,
        ),
        (
            OBJ2,
            JSON2,
            json.read,
            partial(json.write, sort_keys=True),
            json_load,
            json_dump,
        ),
        (
            OBJ1,
            YAML1,
            yaml.read,
            yaml.write,
            yaml_round_trip_load,
            yaml_round_trip_dump,
        ),
        (
            OBJ2,
            YAML2,
            yaml.read,
            yaml.write,
            yaml_round_trip_load,
            yaml_round_trip_dump,
        ),
    ],
)
def test_read_write(
    obj: Any,
    text: str,
    read: Callable,
    write: Callable,
    legacy_dump: Callable | None,
    legacy_load: Callable | None,
):
    assert read(text=text) == obj
    assert write(obj) == text

    if legacy_load:
        assert legacy_load(text) == obj
    if legacy_dump:
        assert legacy_dump(obj) == text


@pytest.mark.parametrize(
    "value,text,write",
    [
        ([SafetyChecks.disabled], "  - disabled\n", yaml.write),
        ([SafetyChecks.warn], "  - warn\n", yaml.write),
        ([SafetyChecks.enabled], "  - enabled\n", yaml.write),
        ([SafetyChecks.disabled], '[\n  "disabled"\n]', json.write),
        ([SafetyChecks.warn], '[\n  "warn"\n]', json.write),
        ([SafetyChecks.enabled], '[\n  "enabled"\n]', json.write),
    ],
)
def test_encode_enum(value: Any, text: str, write: Callable):
    assert write(value) == text


YAML_COMMENT = """
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
""".lstrip()


def test_comment_round_trip():
    assert yaml.write(yaml.read(text=YAML_COMMENT)) == YAML_COMMENT
