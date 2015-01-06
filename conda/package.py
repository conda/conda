try:
    from collections import UserDict
except ImportError:
    from UserDict import UserDict
import yaml


def from_file(filename):
    with open(filename, "rb") as f:
        return Package(**yaml.load(f))


class Package(UserDict, object):
    def __init__(self, *args, **kwargs):
        super(Package, self).__init__(*args, **kwargs)
        if not 'depends' in self:
            self['depends'] = []
