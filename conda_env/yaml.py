"""
Wrapper around yaml to ensure that everything is ordered correctly.

This is based on the answer at http://stackoverflow.com/a/16782282
"""
from __future__ import absolute_import, print_function
from collections import OrderedDict
import yaml


class UnsortableList(list):
    def sort(self, *args, **kwargs):
        pass


class UnsortableOrderedDict(OrderedDict):
    def items(self, *args, **kwargs):
        return UnsortableList(OrderedDict.items(self, *args, **kwargs))


yaml.add_representer(
    UnsortableOrderedDict,
    yaml.representer.SafeRepresenter.represent_dict
)

dump = yaml.dump
load = yaml.load
dict = UnsortableOrderedDict
