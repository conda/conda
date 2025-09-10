# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""YAML and JSON serialization and deserialization functions."""

from __future__ import annotations

import functools
from io import StringIO
from logging import getLogger
from typing import TYPE_CHECKING

from ...deprecations import deprecated
from .json import CondaJSONEncoder, loads

if TYPE_CHECKING:
    from io import IO

    from ..path import PathType

    TextCacheKey = tuple[str, None, None]
    FileCacheKey = tuple[None, IO[str], None]
    PathCacheKey = tuple[None, None, PathType]
    CacheKey = TextCacheKey | FileCacheKey | PathCacheKey

log = getLogger(__name__)


@deprecated(
    "26.3",
    "26.9",
    addendum="Use `conda.common.serialize.yaml._yaml()` instead.",
)
@functools.cache
def _yaml_round_trip():
    import ruamel.yaml as yaml

    parser = yaml.YAML(typ="rt")
    parser.indent(mapping=2, offset=2, sequence=4)
    return parser


@deprecated(
    "26.3",
    "26.9",
    addendum="Use `conda.common.serialize.yaml._yaml()` instead.",
)
@functools.cache
def _yaml_safe():
    import ruamel.yaml as yaml

    parser = yaml.YAML(typ="safe", pure=True)
    parser.indent(mapping=2, offset=2, sequence=4)
    parser.default_flow_style = False
    parser.sort_base_mapping_type_on_output = False
    return parser


@deprecated(
    "26.3",
    "26.9",
    addendum="Use `conda.common.serialize.yaml.load()` instead.",
)
def yaml_round_trip_load(string):
    return _yaml_round_trip().load(string)


@deprecated(
    "26.3",
    "26.9",
    addendum="Use `conda.common.serialize.yaml.load()` instead.",
)
def yaml_safe_load(string):
    """
    Examples:
        >>> yaml_safe_load("key: value")
        {'key': 'value'}

    """
    return _yaml_safe().load(string)


@deprecated(
    "26.3",
    "26.9",
    addendum="Use `conda.common.serialize.yaml.dump()` instead.",
)
def yaml_round_trip_dump(object, stream=None):
    """Dump object to string or stream."""
    ostream = stream or StringIO()
    _yaml_round_trip().dump(object, ostream)
    if not stream:
        return ostream.getvalue()


@deprecated(
    "26.3",
    "26.9",
    addendum="Use `conda.common.serialize.yaml.dump()` instead.",
)
def yaml_safe_dump(object, stream=None):
    """Dump object to string or stream."""
    ostream = stream or StringIO()
    _yaml_safe().dump(object, ostream)
    if not stream:
        return ostream.getvalue()


deprecated.constant(
    "26.3",
    "26.9",
    "EntityEncoder",
    CondaJSONEncoder,
    addendum="Use `conda.common.serialize.json.CondaJSONEncoder` instead.",
)
del CondaJSONEncoder
deprecated.constant(
    "26.3",
    "26.9",
    "json_load",
    loads,
    addendum="Use `conda.common.serialize.json.loads(sort_keys=True)` instead.",
)
del loads


@deprecated(
    "26.3",
    "26.9",
    addendum="Use `conda.common.serialize.json.dumps(sort_keys=True)` instead.",
)
def json_dump(object):
    from .json import dumps

    return dumps(object, sort_keys=True)
