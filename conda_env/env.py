from __future__ import absolute_import, print_function
from collections import OrderedDict
from copy import copy
import os
import yaml

# TODO This should never have to import from conda.cli
from conda.cli import common
from conda.cli import main_list
from conda import install

from . import exceptions


# TODO This should lean more on conda instead of divining it from the outside
# TODO tests!!!
def from_environment(name, prefix):
    installed = install.linked(prefix)
    conda_pkgs = copy(installed)
    # json=True hides the output, data is added to installed
    main_list.add_pip_installed(prefix, installed, json=True)

    pip_pkgs = sorted(installed - conda_pkgs)

    dependencies = ['='.join(a.rsplit('-', 2)) for a in sorted(conda_pkgs)]
    if len(pip_pkgs) > 0:
        dependencies.append({'pip': ['=='.join(a.rsplit('-', 2)[:2]) for a in pip_pkgs]})

    return Environment(name=name, raw_dependencies=dependencies)


def from_file(filename):
    if not os.path.exists(filename):
        raise exceptions.EnvironmentFileNotFound(filename)
    with open(filename, 'rb') as fp:
        data = yaml.load(fp)
    if 'dependencies' in data:
        data['raw_dependencies'] = data['dependencies']
        del data['dependencies']
    return Environment(**data)


class Environment(object):
    def __init__(self, name=None, channels=None, raw_dependencies=None):
        self.name = name
        self._dependencies = None
        self._parsed = False

        if raw_dependencies is None:
            raw_dependencies = {}
        self.raw_dependencies = raw_dependencies

        if channels is None:
            channels = []
        self.channels = channels

    @property
    def dependencies(self):
        if self._dependencies is None:
            self.parse()
        return self._dependencies

    def to_dict(self):
        d = {'name': self.name}
        if self.channels:
            d['channels'] = self.channels
        if self.raw_dependencies:
            d['raw_dependencies'] = self.raw_dependencies
        return d

    def to_yaml(self, stream=None):
        d = self.to_dict()
        if 'raw_dependencies' in d:
            d['dependencies'] = d['raw_dependencies']
            del d['raw_dependencies']
        if stream is None:
            return unicode(yaml.dump(d))
        else:
            yaml.dump(d, default_flow_style=False, stream=stream)

    def parse(self):
        if not self.raw_dependencies:
            self._dependencies = []
            return

        self._dependencies = OrderedDict([('conda', [])])

        for line in self.raw_dependencies:
            if type(line) is dict:
                self._dependencies.update(line)
            else:
                self._dependencies['conda'].append(common.spec_from_line(line))
