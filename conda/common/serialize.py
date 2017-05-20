# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import json
from logging import getLogger

from .._vendor.auxlib.decorators import memoize
from .._vendor.auxlib.entity import EntityEncoder

log = getLogger(__name__)


@memoize
def get_yaml():
    try:
        import ruamel_yaml as yaml
    except ImportError:  # pragma: no cover
        try:
            import ruamel.yaml as yaml
        except ImportError:
            raise ImportError("No yaml library available.\n"
                              "To proceed, conda install "
                              "ruamel_yaml")
    return yaml


def yaml_load(string):
    yaml = get_yaml()
    return yaml.load(string, Loader=yaml.RoundTripLoader, version="1.2")


def yaml_dump(object):
    """dump object to string"""
    yaml = get_yaml()
    return yaml.dump(object, Dumper=yaml.RoundTripDumper,
                     block_seq_indent=2, default_flow_style=False,
                     indent=2)


def json_load(string):
    return json.loads(string)


def json_dump(object):
    return json.dumps(object, indent=2, sort_keys=True,
                      separators=(',', ': '), cls=EntityEncoder)
