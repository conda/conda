# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
from logging import getLogger
import sys

log = getLogger(__name__)


# @memoized
def get_yaml():
    try:
        import ruamel_yaml as yaml
    except ImportError:
        try:
            import ruamel.yaml as yaml
        except ImportError:
            try:
                import yaml
            except ImportError:
                sys.exit("No yaml library available.\n"
                         "To proceed, please conda install ruamel_yaml")
    return yaml


def yaml_load(filehandle):
    yaml = get_yaml()
    try:
        return yaml.load(filehandle, Loader=yaml.RoundTripLoader, version="1.2")
    except AttributeError:
        return yaml.load(filehandle)


def yaml_dump(string):
    yaml = get_yaml()
    try:
        return yaml.dump(string, Dumper=yaml.RoundTripDumper,
                         block_seq_indent=2, default_flow_style=False,
                         indent=4)
    except AttributeError:
        return yaml.dump(string, default_flow_style=False)
