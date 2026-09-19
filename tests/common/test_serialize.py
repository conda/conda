# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from contextlib import nullcontext
from functools import partial
from io import StringIO
from typing import TYPE_CHECKING

import pytest

from conda.base.constants import SafetyChecks
from conda.common import serialize
from conda.common.serialize import (
    json,
    yaml,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
    from typing import Any


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
    "obj,text,read,write",
    [
        (
            OBJ1,
            JSON1,
            json.read,
            partial(json.write, sort_keys=True),
        ),
        (
            OBJ2,
            JSON2,
            json.read,
            partial(json.write, sort_keys=True),
        ),
        (
            OBJ1,
            YAML1,
            yaml.read,
            yaml.write,
        ),
        (
            OBJ2,
            YAML2,
            yaml.read,
            yaml.write,
        ),
    ],
)
def test_read_write(
    obj: Any,
    text: str,
    read: Callable,
    write: Callable,
    tmp_path: Path,
):
    # Test read/write text
    assert read(text=text) == obj
    assert write(obj) == text

    # Test read/write from path
    test_file = tmp_path / "test_file"
    assert write(obj, path=test_file) is None
    assert read(path=test_file) == obj

    # Test read/write from fp
    stream = StringIO()
    assert write(obj, fp=stream) is None
    assert stream.getvalue() == text
    with open(test_file) as fp:
        assert read(fp=fp) == obj


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


@pytest.mark.parametrize(
    "function,raises",
    [
        ("_yaml_round_trip", None),
        ("_yaml_safe", None),
        ("yaml_round_trip_load", TypeError),
        ("yaml_safe_load", TypeError),
        ("yaml_round_trip_dump", TypeError),
        ("yaml_safe_dump", TypeError),
    ],
)
def test_deprecations(function: str, raises: type[Exception] | None) -> None:
    raises_context = pytest.raises(raises) if raises else nullcontext()
    with pytest.deprecated_call(), raises_context:
        getattr(serialize, function)()


def test_yaml_write_path_is_atomic_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """A failure partway through yaml.write(path=...) must not truncate
    an existing file (gh-16694).
    """
    import os

    test_file = tmp_path / "condarc"
    test_file.write_text("channels:\n  - conda-forge\n")

    real_fsync = os.fsync

    def failing_fsync(fd: int) -> None:
        real_fsync(fd)
        raise OSError(27, "File too large")

    monkeypatch.setattr(os, "fsync", failing_fsync)
    with pytest.raises(OSError, match="File too large"):
        yaml.write(OBJ1, path=test_file)

    # original contents are untouched
    assert test_file.read_text() == "channels:\n  - conda-forge\n"
    # no temporary files are left behind
    assert list(tmp_path.iterdir()) == [test_file]


def test_yaml_write_path_preserves_file_mode(tmp_path: Path):
    """yaml.write(path=...) keeps the existing file's permissions."""
    import os
    import stat

    test_file = tmp_path / "condarc"
    test_file.write_text("channels:\n  - conda-forge\n")
    mode = test_file.stat().st_mode
    # make the file's mode distinctive (group/other read-only vs default)
    os.chmod(test_file, mode | stat.S_IRGRP)

    yaml.write(OBJ1, path=test_file)

    assert yaml.read(path=test_file) == OBJ1
    assert test_file.stat().st_mode == (mode | stat.S_IRGRP)
