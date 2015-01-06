try:
    from collections import UserDict
except ImportError:
    from UserDict import UserDict
import yaml

from . import exceptions


def from_file(filename):
    try:
        with open(filename, "rb") as f:
            return Package(**yaml.load(f))
    except IOError:
        raise exceptions.FileNotFound()


class Package(UserDict, object):
    def __init__(self, *args, **kwargs):
        super(Package, self).__init__(*args, **kwargs)
        if not 'depends' in self:
            self['depends'] = []
