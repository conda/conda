# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from functools import partial
from io import StringIO
from threading import Barrier
from typing import TYPE_CHECKING

import pytest
from ruamel.yaml import YAML
from ruamel.yaml.parser import ParserError
from ruamel.yaml.representer import RepresenterError

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

    from pytest_mock import MockerFixture


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


@pytest.fixture(
    params=[
        "yaml",
        pytest.param(
            "round_trip",
            marks=pytest.mark.filterwarnings("ignore:conda.common.serialize:Warning"),
        ),
        pytest.param(
            "safe",
            marks=pytest.mark.filterwarnings("ignore:conda.common.serialize:Warning"),
        ),
    ],
)
def yaml_api(request: pytest.FixtureRequest) -> tuple[Callable, Callable]:
    if request.param == "yaml":
        return yaml.loads, yaml.dumps
    return (
        getattr(serialize, f"yaml_{request.param}_load"),
        getattr(serialize, f"yaml_{request.param}_dump"),
    )


def test_yaml_concurrent_loads(
    yaml_api: tuple[Callable, Callable], mocker: MockerFixture
) -> None:
    load, _ = yaml_api
    assert load(YAML1) == OBJ1
    barrier = Barrier(2, timeout=10)
    get_constructor_parser = YAML.get_constructor_parser

    def synchronized_parser(self, stream):
        result = get_constructor_parser(self, stream)
        # Both streams must be assigned before either thread starts parsing.
        barrier.wait()
        return result

    mocker.patch.object(YAML, "get_constructor_parser", synchronized_parser)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(load, (YAML1, YAML2)))

    assert results == [OBJ1, OBJ2]


def test_yaml_concurrent_dumps(
    yaml_api: tuple[Callable, Callable], mocker: MockerFixture
) -> None:
    _, dump = yaml_api
    assert YAML(typ="safe").load(dump(OBJ1)) == OBJ1
    barrier = Barrier(2, timeout=10)
    get_serializer_representer_emitter = YAML.get_serializer_representer_emitter

    def synchronized_emitter(self, stream, tlca):
        result = get_serializer_representer_emitter(self, stream, tlca)
        # Both output streams must be assigned before either thread starts dumping.
        barrier.wait()
        return result

    mocker.patch.object(
        YAML, "get_serializer_representer_emitter", synchronized_emitter
    )
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(dump, (OBJ1, OBJ2)))

    assert [YAML(typ="safe").load(text) for text in results] == [OBJ1, OBJ2]


def test_yaml_load_after_error(yaml_api: tuple[Callable, Callable]) -> None:
    load, _ = yaml_api
    with pytest.raises(ParserError):
        load("%YAML 1.1\n---\na: [\n")

    # The failed document must not leave subsequent loads using YAML 1.1.
    assert load("value: yes\n") == {"value": "yes"}


def test_yaml_dump_after_error(yaml_api: tuple[Callable, Callable]) -> None:
    _, dump = yaml_api
    with pytest.raises((TypeError, RepresenterError)):
        dump(object())

    assert YAML(typ="safe").load(dump(OBJ1)) == OBJ1


@pytest.mark.filterwarnings("ignore:conda.common.serialize:Warning")
@pytest.mark.parametrize(
    "load,dump",
    [
        (yaml.loads, yaml.dumps),
        (serialize.yaml_round_trip_load, serialize.yaml_round_trip_dump),
    ],
    ids=["yaml", "round_trip"],
)
@pytest.mark.parametrize(
    "handle,prefix,expected_tag",
    [
        ("!e!", "tag:example.com,2020:", "tag:example.com,2020:foo"),
        ("!", "tag:example.com,2020:", "tag:example.com,2020:foo"),
        ("!e!", "tag:example.com%2C2020:", "tag:example.com%2C2020:foo"),
    ],
)
def test_yaml_tag_round_trip(
    load: Callable, dump: Callable, handle: str, prefix: str, expected_tag: str
) -> None:
    obj = load(f"%TAG {handle} {prefix}\n---\nvalue: {handle}foo bar\n")
    assert str(obj["value"].tag) == expected_tag
    result = load(dump(obj))

    assert result["value"].value == "bar"
    assert str(result["value"].tag) == expected_tag


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
