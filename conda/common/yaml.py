# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals
from logging import getLogger

from .._vendor.auxlib.decorators import memoize

log = getLogger(__name__)


@memoize
def get_yaml():
    try:
        import ruamel_yaml as yaml
    except ImportError:                                         # pragma: no cover
        try:                                                    # pragma: no cover
            import ruamel.yaml as yaml                          # pragma: no cover
        except ImportError:                                     # pragma: no cover
            raise ImportError("No yaml library available.\n"    # pragma: no cover
                              "To proceed, conda install "      # pragma: no cover
                              "ruamel_yaml")                    # pragma: no cover
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
