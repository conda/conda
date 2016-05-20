# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
from collections import OrderedDict, namedtuple
from glob import glob
from itertools import chain
from logging import getLogger
import os
from platform import machine
import sys
from stat import S_IFREG, S_IFDIR, S_IFMT

from enum import Enum
from os.path import join, expandvars, expanduser, normpath
from os import stat

from six import iteritems

from auxlib._vendor.five import with_metaclass
from auxlib.exceptions import ThisShouldNeverHappenError
from auxlib.type_coercion import typify
from auxlib.ish import dals

from ..common.yaml import yaml_load

log = getLogger(__name__)


def expand(path):
    return normpath(expanduser(expandvars(path)))


def first(iterable, key=lambda x: bool(x), default=None, apply=lambda x: x):
    """Give the first value that satisfies the key test.

    Args:
        iterable:
        key (callable): test for each element of iterable
        default: returned when all elements fail test
        apply (callable): applied to element before return

    Returns: first element in iterable mutated with optional apply that passes key

    Examples:
        >>> first([0, False, None, [], (), 42])
        42
        >>> first([0, False, None, [], ()]) is None
        True
        >>> first([0, False, None, [], ()], default='ohai')
        'ohai'
        >>> import re
        >>> m = first(re.match(regex, 'abc') for regex in ['b.*', 'a(.*)'])
        >>> m.group(1)
        'bc'
        The optional `key` argument specifies a one-argument predicate function
        like that used for `filter()`.  The `key` argument, if supplied, must be
        in keyword form.  For example:
        >>> first([1, 1, 3, 4, 5], key=lambda x: x % 2 == 0)
        4

    """
    return next((apply(x) for x in iterable if key(x)), default)


def last(iterable, key=lambda x: bool(x), default=None, apply=lambda x: x):
    return next((apply(x) for x in reversed(iterable) if key(x)), default)


class Arch(Enum):
    x86 = 'x86'
    x86_64 = 'x86_64'
    armv6l = 'armv6l'
    armv7l = 'armv7l'
    ppc64le = 'ppc64le'

    @classmethod
    def from_sys(cls):
        return cls[machine()]


class Platform(Enum):
    linux = 'linux'
    win = 'win32'
    openbsd = 'openbsd5'
    osx = 'darwin'

    @classmethod
    def from_sys(cls):
        return cls(sys.platform)

machine_bits = 8 * tuple.__itemsize__


UID = os.getuid()
PWD = os.getcwd()
CONDA = 'CONDA'
CONDA_ = 'CONDA_'
conda = 'conda'


FROM_ENV = dict((key.replace('CONDA_', '').lower(), value)
                for key, value in os.environ.items()
                if key.startswith(CONDA_))


SEARCH_PATH = (
    '/etc/conda/condarc',
    '/etc/conda/condarc.d/',
    '/var/lib/conda/condarc',
    '/var/lib/conda/condarc.d/',
    '$HOME/.conda/condarc',
    '$HOME/.conda/condarc.d/',
    '$HOME/.condarc',
    '$ENV/.condarc',
    '$ENV/.condaenv.yml',
)


def load_raw_configs():
    # returns an ordered map of filepath and raw yaml dict

    def _load_yaml(full_path):
        with open(full_path, 'r') as fh:
            return yaml_load(fh)

    def _file_yaml_loader(fullpath):
        yield fullpath, _load_yaml(fullpath)

    def _dir_yaml_loader(fullpath):
        for filepath in glob(join(fullpath, "*.yml")):
            yield filepath, _load_yaml(filepath)

    # map a stat result to a file loader or a directory loader
    _loader = {
        S_IFREG: _file_yaml_loader,
        S_IFDIR: _dir_yaml_loader,
    }

    def _get_st_mode(path):
        # stat the path for file type, or None if path doesn't exist
        try:
            return S_IFMT(stat(path).st_mode)
        except OSError:
            return None

    expanded_paths = tuple(expand(path) for path in SEARCH_PATH)
    stat_paths = (_get_st_mode(path) for path in expanded_paths)
    load_paths = (_loader[st_mode](path)
                  for path, st_mode in zip(expanded_paths, stat_paths)
                  if st_mode is not None)
    raw_data = OrderedDict(kv for kv in chain.from_iterable(load_paths))
    return raw_data


def get_yaml_eol_comment(yaml_dict, key):
    try:
        return yaml_dict._yaml_comment.items[key][2].value
    except (AttributeError, KeyError):  # probably could add IndexError here too and be just fine
        return None


def extract_value_and_flags(yaml_dict, key):
    value = typify(yaml_dict[key])
    comment = get_yaml_eol_comment(yaml_dict, key)
    is_important = comment and '!important' in comment
    return value, is_important


Match = namedtuple('Match', ['filepath', 'key', 'value', 'isimportant'])
NO_MATCH = Match(None, None, None, None)

class Parameter(object):
    # inheritance model
    # name = None
    # help = None
    # alternate names (aliases)
    # default
    # validation?

    def __init__(self, default, aliases=()):
        self._name = None
        self._names = None
        self.default = default
        self.type = type(default)
        self.aliases = aliases

    def set_name(self, name):
        # this is an explicit method, and not a descriptor setter
        # it's meant to be called by the Configuration metaclass
        self._name = name
        self._names = frozenset(x for x in chain(self.aliases, (name, )))

    @property
    def name(self):
        if self._name is None:
            raise ThisShouldNeverHappenError()
        return self._name

    @property
    def names(self):
        if self._names is None:
            raise ThisShouldNeverHappenError()
        return self._names

    def _get_key_value_isimportant(self, filepath, yaml_dict):
        keys = self.names & yaml_dict.keys()
        numkeys = len(keys)
        if numkeys == 0:
            return NO_MATCH
        elif numkeys == 1:
            key = keys.pop()
            value, is_important = extract_value_and_flags(yaml_dict, key)
            return Match(filepath, key, value, is_important)
        else:
            # when multiple aliases exist, default to the named key
            assert self.name in keys, "conda doctor should help here"
            key = self.name
            value, is_important = extract_value_and_flags(yaml_dict, key)
            return Match(filepath, key, value, is_important)

    def __get__(self, instance, instance_type):
        array = tuple(self._get_key_value_isimportant(filepath, yaml_dict)
                      for filepath, yaml_dict in iteritems(instance.raw_data))
        important_match = first(array, lambda x: x.isimportant, default=NO_MATCH)
        last_match = last(array, lambda x: x is not NO_MATCH, default=NO_MATCH)
        final_value = first((important_match.value, last_match.value, self.default),
                            lambda x: x is not None)
        return final_value


class ConfigurationType(type):

    def __init__(cls, name, bases, attr):
        super(ConfigurationType, cls).__init__(name, bases, attr)
        any(field.set_name(name)
            for name, field in iteritems(cls.__dict__)
            if isinstance(field, Parameter))


@with_metaclass(ConfigurationType)
class Configuration(object):

    def __init__(self, raw_data):
        self.raw_data = raw_data

    add_pip_as_python_dependency = Parameter(default=True)
    always_yes = Parameter(False)
    always_copy = Parameter(False)
    changeps1 = Parameter(True)
    use_pip = Parameter(True)
    binstar_upload = Parameter(None, aliases=('anaconda_upload', ))
    allow_softlinks = Parameter(True)
    self_update = Parameter(True)
    show_channel_urls = Parameter(None)
    update_dependencies = Parameter(True)
    channel_priority = Parameter(True)
    ssl_verify = Parameter(True)
    track_features = Parameter(None)


def get_help_dict():
    # this is a function so that most of the time it's not evaluated and loaded into memory
    return {
        'add_pip_as_python_dependency': dals("""
            """),
        'always_yes': dals("""
            """),
        'always_copy': dals("""
            """),
        'changeps1': dals("""
            """),
        'use_pip': dals("""
            Use pip when listing packages with conda list. Note that this does not affect any
            conda command or functionality other than the output of the command conda list.
            """),
        'binstar_upload': dals("""
            """),
        'allow_softlinks': dals("""
            """),
        'self_update': dals("""
            """),
        'show_channel_urls': dals("""
            # show channel URLs when displaying what is going to be downloaded
            # None means letting conda decide
            """),
        'update_dependencies': dals("""
            """),
        'channel_priority': dals("""
            """),
        'ssl_verify': dals("""
            """),
    }





# rc_list_keys = [
#     'channels',
#     'disallow',
#     'create_default_packages',
#     'track_features',
#     'envs_dirs',
#     'default_channels',
# ]
# disallow = set(rc.get('disallow', []))  # set packages disallowed to be installed
# create_default_packages = list(rc.get('create_default_packages', []))  # packages which are added to a newly created environment by default
# track_features = set(rc['track_features'])




if __name__ == "__main__":
    config = Configuration(load_raw_configs())
    print(config.raw_data)
    assert config.always_yes is False
    assert config.show_channel_urls is None
    assert config.binstar_upload is None
    assert isinstance(config.track_features, set)
    # import pdb; pdb.set_trace()

