from __future__ import absolute_import, print_function
from collections import OrderedDict
from copy import copy
import os
import re
import sys

# TODO This should never have to import from conda.cli
from conda.cli import common
from conda import install
from conda import config

from . import compat
from . import exceptions
from . import yaml
from conda_env.pip_util import add_pip_installed


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
def from_environment(name, prefix, no_builds=False):
    installed = install.linked(prefix)
    conda_pkgs = copy(installed)
    # json=True hides the output, data is added to installed
    add_pip_installed(prefix, installed, json=True)

    pip_pkgs = sorted(installed - conda_pkgs)

    if no_builds:
        dependencies = ['='.join(a.rsplit('-', 2)[0:2]) for a in sorted(conda_pkgs)]
    else:
        dependencies = ['='.join(a.rsplit('-', 2)) for a in sorted(conda_pkgs)]
    if len(pip_pkgs) > 0:
        dependencies.append({'pip': ['=='.join(a.rsplit('-', 2)[:2]) for a in pip_pkgs]})

    channels = config.get_rc_urls()

    return Environment(name=name, dependencies=dependencies, channels=channels)


def from_yaml(yamlstr, **kwargs):
    """Load and return a ``Environment`` from a given ``yaml string``"""
    data = yaml.load(yamlstr)
    if kwargs is not None:
        for key, value in kwargs.items():
            data[key] = value
    return Environment(**data)


def custom_selectors_from_yaml(yamlstr):
    """Load and return a list of custom selectors from a given ``yaml string``"""
    data = yaml.load(yamlstr)
    if 'selectors' in data:
        return data['selectors']
    return []


def from_file(filename, selectors=None):
    if not os.path.exists(filename):
        raise exceptions.EnvironmentFileNotFound(filename)
    with open(filename, 'r') as fp:
        yamlstr = fp.read()
        custom_selectors = custom_selectors_from_yaml(yamlstr)
        yamlstr = select_lines(yamlstr, filename, custom_selectors, selectors=selectors)
        return from_yaml(yamlstr, filename=filename)


def ns_cfg(custom_selectors, selectors=None):
    plat = sys.platform  # see https://docs.python.org/2/library/sys.html#sys.platform
    is_x64 = sys.maxsize > 2**32  # from https://docs.python.org/2/library/platform.html#cross-platform
    d = dict(
        linux=plat.startswith('linux'),
        linux32=plat.startswith('linux') and not is_x64,
        linux64=plat.startswith('linux') and is_x64,
        osx=plat.startswith('darwin'),
        win=plat.startswith('win32'),
        win32=plat.startswith('win32') and not is_x64,
        win64=plat.startswith('win32') and is_x64,
        unix=plat.startswith(('linux', 'darwin')),
        unix32=plat.startswith(('linux', 'darwin')) and not is_x64,
        unix64=plat.startswith(('linux', 'darwin')) and is_x64,
        x86=not is_x64,
        x64=is_x64,
        os=os,
        environ=os.environ,
    )
    if selectors is None:
        selectors = []
    selector_dict = dict((s, s in selectors) for s in custom_selectors)
    d.update(selector_dict)
    return d


sel_pat = re.compile(r'(.+?)\s*(#.*)?\[(.+)\](?(2).*)$')
def select_lines(yamlstr, filename, custom_selectors, selectors=None):
    if selectors and len(selectors) == 1 and selectors[0] == "all":
        selectors = custom_selectors
    namespace = ns_cfg(custom_selectors, selectors)
    lines = []
    orig_lines = yamlstr.splitlines()
    for i, line in enumerate(orig_lines):
        line = line.rstrip()
        if line.lstrip().startswith('#'):
            continue  # Don't bother with comment only lines
        m = sel_pat.match(line)
        if m:
            # condition found, eval it
            cond = m.group(3)
            try:
                if eval(cond, namespace, {}):
                    lines.append(orig_lines[i])
            except NameError:
                continue  # if a selector is undefined, that equates to False
            except Exception as e:
                sys.exit('''\
Error: Invalid selector in %s line %d:
%s
''' % (filename, i + 1, line))
            continue
        else:
            # no condition
            lines.append(line)
    return '\n'.join(lines) + '\n'



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


class Environment(object):
    def __init__(self, name=None, filename=None, channels=None,
                 dependencies=None, selectors=None):
        self.name = name
        self.filename = filename
        self.dependencies = Dependencies(dependencies)

        if channels is None:
            channels = []
        self.channels = channels

        if selectors is None:
            selectors = []
        self.selectors = selectors

    def add_channels(self, channels=[]):
        self.channels = list(set(self.channels + channels))

    def remove_channels(self):
        self.channels = []

    def to_dict(self):
        d = yaml.dict([('name', self.name)])
        if self.channels:
            d['channels'] = self.channels
        if self.dependencies:
            d['dependencies'] = self.dependencies.raw
        if self.selectors:
            d['selectors'] = self.selectors
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
