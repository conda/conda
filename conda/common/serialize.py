# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import json
from logging import getLogger
import re

from .compat import PY2, odict, ensure_text_type
from .._vendor.auxlib.decorators import memoize
from .._vendor.auxlib.entity import EntityEncoder

log = getLogger(__name__)


class LazyEval(object):
    init_count = 0
    eval_count = 0

    def __init__(self, func, *args, **kwargs):
        LazyEval.init_count += 1

        def lazy_self():
            LazyEval.eval_count += 1
            return_value = func(*args, **kwargs)
            object.__setattr__(self, "lazy_self", lambda: return_value)
            return return_value
        object.__setattr__(self, "lazy_self", lazy_self)

    def __getattribute__(self, name):
        lazy_self = object.__getattribute__(self, "lazy_self")
        if name == "lazy_self":
            return lazy_self
        return getattr(lazy_self(), name)

    def __setattr__(self, name, value):
        setattr(self.lazy_self(), name, value)


class LazyFunc:
    def __init__(self, func):
        self.func = func

    def __call__(self, *args, **kwargs):
        return LazyEval(self.func, *args, **kwargs)


@memoize
def get_yaml():
    try:
        re.compile = LazyFunc(re.compile)
        import ruamel_yaml as yaml
    except ImportError:  # pragma: no cover
        try:
            import ruamel.yaml as yaml
        except ImportError:
            raise ImportError("No yaml library available.\n"
                              "To proceed, conda install "
                              "ruamel_yaml")
    finally:
        re.compile = re.compile.func
    return yaml


yaml = get_yaml()


def represent_ordereddict(dumper, data):
    value = []

    for item_key, item_value in data.items():
        node_key = dumper.represent_data(item_key)
        node_value = dumper.represent_data(item_value)

        value.append((node_key, node_value))

    return yaml.nodes.MappingNode(u'tag:yaml.org,2002:map', value)


yaml.representer.RoundTripRepresenter.add_representer(odict, represent_ordereddict)

if PY2:
    def represent_unicode(self, data):
        return self.represent_str(data.encode('utf-8'))


    yaml.representer.RoundTripRepresenter.add_representer(unicode, represent_unicode)  # NOQA


def yaml_load(string):
    return yaml.load(string, Loader=yaml.RoundTripLoader, version="1.2")


def yaml_load_safe(string):
    """
    Examples:
        >>> yaml_load_safe("key: value")
        {'key': 'value'}

    """
    return yaml.load(string, Loader=yaml.SafeLoader, version="1.2")


def yaml_load_standard(string):
    """Uses the default (unsafe) loader.

    Examples:
        >>> yaml_load_standard("prefix: !!python/unicode '/Users/darwin/test'")
        {'prefix': '/Users/darwin/test'}
    """
    return yaml.load(string, Loader=yaml.Loader, version="1.2")


def yaml_dump(object):
    """dump object to string"""
    return yaml.dump(object, Dumper=yaml.RoundTripDumper,
                     block_seq_indent=2, default_flow_style=False,
                     indent=2)


def json_load(string):
    return json.loads(string)


def json_dump(object):
    return ensure_text_type(json.dumps(object, indent=2, sort_keys=True,
                                       separators=(',', ': '), cls=EntityEncoder))
