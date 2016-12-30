from __future__ import absolute_import, print_function

import os
from collections import OrderedDict
from conda.base.context import context
from conda.cli import common  # TODO: this should never have to import form conda.cli
from conda.core.linked_data import linked
from copy import copy
from itertools import chain

from . import compat, exceptions, yaml
from .pip_util import add_pip_installed

def load_from_directory(directory):
    """Load and return an ``Environment`` from a given ``directory``"""
    files = ['environment.yml', 'environment.yaml']
    while True:
        for f in files:
            try:
                return from_file(os.path.join(directory, f))
            except exceptions.EnvironmentFileNotFound:
                pass
        old_directory = directory
        directory = os.path.dirname(directory)
        if directory == old_directory:
            break
    raise exceptions.EnvironmentFileNotFound(files[0])


# TODO This should lean more on conda instead of divining it from the outside
# TODO tests!!!
def from_environment(name, prefix, no_builds=False, ignore_channels=False):
    """
        Get environment object from prefix
    Args:
        name: The name of environment
        prefix: The path of prefix
        no_builds: Whether has build requirement
        ignore_channels: whether ignore_channels

    Returns:     Environment object
    """
    installed = linked(prefix, ignore_channels=ignore_channels)
    conda_pkgs = copy(installed)
    # json=True hides the output, data is added to installed
    add_pip_installed(prefix, installed, json=True)

    pip_pkgs = sorted(installed - conda_pkgs)

    if no_builds:
        dependencies = ['='.join(a.quad[0:3]) for a in sorted(conda_pkgs)]
    else:
        dependencies = ['='.join(a.quad[0:3]) for a in sorted(conda_pkgs)]
    if len(pip_pkgs) > 0:
        dependencies.append({'pip': ['=='.join(a.rsplit('-', 2)[:2]) for a in pip_pkgs]})
    # conda uses ruamel_yaml which returns a ruamel_yaml.comments.CommentedSeq
    # this doesn't dump correctly using pyyaml
    channels = list(context.channels)
    if not ignore_channels:
        for dist in conda_pkgs:
            if dist.channel not in channels:
                channels.insert(0, dist.channel)
    return Environment(name=name, dependencies=dependencies, channels=channels, prefix=prefix)


def from_yaml(yamlstr, **kwargs):
    """Load and return a ``Environment`` from a given ``yaml string``"""
    data = yaml.load(yamlstr)
    if kwargs is not None:
        for key, value in kwargs.items():
            data[key] = value
    return Environment(**data)


def from_file(filename):
    if not os.path.exists(filename):
        raise exceptions.EnvironmentFileNotFound(filename)
    with open(filename, 'r') as fp:
        yamlstr = fp.read()
        return from_yaml(yamlstr, filename=filename)


# TODO test explicitly
class Dependencies(OrderedDict):
    def __init__(self, raw, *args, **kwargs):
        super(Dependencies, self).__init__(*args, **kwargs)
        self.raw = raw
        self.parse()

    def parse(self):
        if not self.raw:
            return

        self.update({'conda': []})

        for line in self.raw:
            if isinstance(line, dict):
                self.update(line)
            else:
                self['conda'].append(common.arg2spec(line))

    # TODO only append when it's not already present
    def add(self, package_name):
        self.raw.append(package_name)
        self.parse()


def unique(seq, key=None):
    """ Return only unique elements of a sequence
    >>> tuple(unique((1, 2, 3)))
    (1, 2, 3)
    >>> tuple(unique((1, 2, 1, 3)))
    (1, 2, 3)
    Uniqueness can be defined by key keyword
    >>> tuple(unique(['cat', 'mouse', 'dog', 'hen'], key=len))
    ('cat', 'mouse')
    """
    seen = set()
    seen_add = seen.add
    if key is None:
        for item in seq:
            if item not in seen:
                seen_add(item)
                yield item
    else:  # calculate key
        for item in seq:
            val = key(item)
            if val not in seen:
                seen_add(val)
                yield item


class Environment(object):
    def __init__(self, name=None, filename=None, channels=None,
                 dependencies=None, prefix=None):
        self.name = name
        self.filename = filename
        self.prefix = prefix
        self.dependencies = Dependencies(dependencies)

        if channels is None:
            channels = []
        self.channels = channels

    def add_channels(self, channels):
        self.channels = list(unique(chain.from_iterable((channels, self.channels))))

    def remove_channels(self):
        self.channels = []

    def to_dict(self):
        d = yaml.dict([('name', self.name)])
        if self.channels:
            d['channels'] = self.channels
        if self.dependencies:
            d['dependencies'] = self.dependencies.raw
        if self.prefix:
            d['prefix'] = self.prefix
        return d

    def to_yaml(self, stream=None):
        d = self.to_dict()
        out = compat.u(yaml.dump(d, default_flow_style=False))
        if stream is None:
            return out
        stream.write(compat.b(out, encoding="utf-8"))

    def save(self):
        with open(self.filename, "wb") as fp:
            self.to_yaml(stream=fp)
