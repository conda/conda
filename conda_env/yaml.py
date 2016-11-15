"""
Wrapper around yaml to ensure that everything is ordered correctly.

This is based on the answer at http://stackoverflow.com/a/16782282
"""
from __future__ import absolute_import, print_function
from collections import OrderedDict

from conda.common.yaml import get_yaml
yaml = get_yaml()


def represent_ordereddict(dumper, data):
    value = []

    for item_key, item_value in data.items():
        node_key = dumper.represent_data(item_key)
        node_value = dumper.represent_data(item_value)

        value.append((node_key, node_value))

    return yaml.nodes.MappingNode(u'tag:yaml.org,2002:map', value)


yaml.add_representer(OrderedDict, represent_ordereddict)

dump = yaml.dump
load = yaml.load
dict = OrderedDict
