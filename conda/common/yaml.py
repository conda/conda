# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals
from logging import getLogger

from .._vendor.auxlib.decorators import memoize

log = getLogger(__name__)


@memoize
def get_yaml():
    try:
        import ruamel_yaml as yaml
    except ImportError:
        import ruamel.yaml as yaml
    return yaml


def yaml_load(filehandle):
    yaml = get_yaml()
    return yaml.load(filehandle, Loader=yaml.RoundTripLoader, version="1.2")


def yaml_dump(obj):
    yaml = get_yaml()
    return yaml.dump(obj, Dumper=yaml.RoundTripDumper,
                     block_seq_indent=2, default_flow_style=False,
                     indent=2)
