# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

import json
from logging import getLogger

from .compat import odict, ensure_text_type
from ..auxlib.entity import EntityEncoder

try:
    import ruamel_yaml as yaml
except ImportError:  # pragma: no cover
    try:
        import ruamel.yaml as yaml
    except ImportError:
        raise ImportError("No yaml library available. To proceed, conda install ruamel_yaml")

log = getLogger(__name__)


def represent_ordereddict(dumper, data):
    value = []

    for item_key, item_value in data.items():
        node_key = dumper.represent_data(item_key)
        node_value = dumper.represent_data(item_value)

        value.append((node_key, node_value))

    return yaml.nodes.MappingNode(u'tag:yaml.org,2002:map', value)


yaml.representer.RoundTripRepresenter.add_representer(odict, represent_ordereddict)
yaml.representer.SafeRepresenter.add_representer(odict, represent_ordereddict)


def yaml_round_trip_load(string):
    return yaml.round_trip_load(string, version="1.2")


def yaml_safe_load(string):
    """
    Examples:
        >>> yaml_safe_load("key: value")
        {'key': 'value'}

    """
    return yaml.safe_load(string, version="1.2")


def yaml_round_trip_dump(object):
    """dump object to string"""
    return yaml.round_trip_dump(
        object, block_seq_indent=2, default_flow_style=False, indent=2
    )


def yaml_safe_dump(object):
    """dump object to string"""
    return yaml.safe_dump(
        object, block_seq_indent=2, default_flow_style=False, indent=2
    )


def json_load(string):
    return json.loads(string)


def json_dump(object):
    return ensure_text_type(json.dumps(object, indent=2, sort_keys=True,
                                       separators=(',', ': '), cls=EntityEncoder))
