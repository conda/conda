# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import os
import sys
from collections import OrderedDict, namedtuple
from glob import glob
from itertools import chain
from logging import getLogger
from os import stat
from os.path import join, expandvars, expanduser, normpath
from platform import machine
from stat import S_IFREG, S_IFDIR, S_IFMT

from auxlib._vendor.five import with_metaclass
from auxlib.exceptions import ThisShouldNeverHappenError
from auxlib.ish import dals
from auxlib.type_coercion import typify
from enum import Enum
from six import iteritems
from toolz.dicttoolz import merge
from toolz.functoolz import excepts
from toolz.itertoolz import concat, unique, concatv

from ..common.yaml import yaml_load

log = getLogger(__name__)


def expand(path):
    return normpath(expanduser(expandvars(path)))


def first(seq, key=lambda x: bool(x), default=None, apply=lambda x: x):
    """Give the first value that satisfies the key test.

    Args:
        seq (iterable):
        key (callable): test for each element of iterable
        default: returned when all elements fail test
        apply (callable): applied to element before return

    Returns: first element in seq that passes key, mutated with optional apply

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
    return next((apply(x) for x in seq if key(x)), default)


def cumfirst(seq, key=lambda x: bool(x), apply=lambda x: x):
    """like first, but cumulative, up to and including first

    unlike first, there is no default; where default would be returned in first, all of seq is returned in cumfirst

    Examples:
        >>> cumfirst([0, False, None, [], (), 42])
        (0, False, None, [], (), 42)
        >>> cumfirst([0, False, 'some', [], (), 42])
        (0, False, 'some')

    """
    lst = []
    for element in seq:
        lst.append(apply(element))
        if key(element):
            break
    return tuple(lst)


def last(seq, key=lambda x: bool(x), default=None, apply=lambda x: x):
    return next((apply(x) for x in reversed(seq) if key(x)), default)


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


def load_raw_configs(search_path=SEARCH_PATH):
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

    expanded_paths = tuple(expand(path) for path in search_path)
    stat_paths = (_get_st_mode(path) for path in expanded_paths)
    load_paths = (_loader[st_mode](path)
                  for path, st_mode in zip(expanded_paths, stat_paths)
                  if st_mode is not None)
    raw_data = OrderedDict(kv for kv in chain.from_iterable(load_paths))
    return raw_data


def get_yaml_key_comment(commented_dict, key):
    try:
        return commented_dict.ca.items[key][2].value.strip()
    except (AttributeError, KeyError):
        return ''


def get_yaml_value_lines_comments(value):
    items = value.ca.items
    raw_comment_lines = tuple(excepts((AttributeError, KeyError, TypeError),
                                      lambda q: items.get(q)[0].value.strip(),
                                      lambda _: ''  # default value on exception
                                      )(q)
                              for q in range(len(value)))
    return raw_comment_lines


def extract_value_and_flags(yaml_dict, key, parameter_type):
    def __extract_for_single(yaml_dict, key):
        value = typify(yaml_dict[key])
        key_comment = get_yaml_key_comment(yaml_dict, key)
        important_lines = (0,) if '!important' in key_comment else ()
        return value, important_lines

    def __extract_for_list(yaml_dict, key):
        yaml_value = yaml_dict[key]
        key_comment = get_yaml_key_comment(yaml_dict, key)
        value_comments = get_yaml_value_lines_comments(yaml_value)
        seq = enumerate(chain((key_comment,), value_comments))
        important_lines = tuple(q for q, comment in seq if '!important' in comment)
        return tuple(value), important_lines

    def __extract_for_map(yaml_dict, key):
        # important_lines now actually needs to be important_keys
        yaml_value = yaml_dict[key]
        key_comment = get_yaml_key_comment(yaml_dict, key)
        mapkeys = tuple(k for k in yaml_value)
        mapkeys_comments = tuple(get_yaml_key_comment(yaml_value, mapkey) for mapkey in mapkeys)
        seq = enumerate(chain((key_comment,), mapkeys_comments))
        important_lines = tuple(mapkeys[q] if q else q  # return the mapkey, not the index
                                for q, comment in seq
                                if '!important' in comment)
        return dict(yaml_value), important_lines

    __extract = {
        ParameterType.single: __extract_for_single,
        ParameterType.list: __extract_for_list,
        ParameterType.map: __extract_for_map,
    }
    return __extract[parameter_type](yaml_dict, key)


Match = namedtuple('Match', ('filepath', 'key', 'value', 'important'))
NO_MATCH = Match(None, None, None, ())


class ParameterType(Enum):
    single = 'single'
    list = 'list'
    map = 'map'


class Parameter(object):
    # inheritance model
    # name = None
    # help = None
    # alternate names (aliases)
    # default
    # validation?

    def __init__(self, default, aliases=(), parameter_type=ParameterType.single):
        self._name = None
        self._names = None
        self.default = default
        self.aliases = aliases
        self.parameter_type = parameter_type

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

    @staticmethod
    def __extract_for_single(yaml_dict, key):
        value = typify(yaml_dict[key])
        key_comment = get_yaml_key_comment(yaml_dict, key)
        important_lines = (0,) if '!important' in key_comment else ()
        return value, important_lines

    @staticmethod
    def __extract_for_list(yaml_dict, key):
        yaml_value = yaml_dict[key]
        key_comment = get_yaml_key_comment(yaml_dict, key)
        value_comments = get_yaml_value_lines_comments(yaml_value)
        seq = enumerate(chain((key_comment,), value_comments))
        important_lines = tuple(q for q, comment in seq if '!important' in comment)
        return tuple(yaml_value), important_lines

    @staticmethod
    def __extract_for_map(yaml_dict, key):
        # important_lines now actually needs to be important_keys
        yaml_value = yaml_dict[key]
        key_comment = get_yaml_key_comment(yaml_dict, key)
        mapkeys = tuple(k for k in yaml_value)
        mapkeys_comments = tuple(get_yaml_key_comment(yaml_value, mapkey) for mapkey in mapkeys)
        seq = enumerate(chain((key_comment,), mapkeys_comments))
        important_lines = tuple(mapkeys[q] if q else q  # return the mapkey, not the index
                                for q, comment in seq
                                if '!important' in comment)
        return dict(yaml_value), important_lines

    __extract = {
        ParameterType.single: __extract_for_single.__func__,
        ParameterType.list: __extract_for_list.__func__,
        ParameterType.map: __extract_for_map.__func__,
    }

    def __get_match(self, filepath, yaml_dict):
        # TODO: cleanup
        keys = self.names & yaml_dict.keys()
        numkeys = len(keys)
        if numkeys == 0:
            return NO_MATCH
        elif numkeys == 1:
            key = keys.pop()
            value, important = self.__extract[self.parameter_type](yaml_dict, key)
            return Match(filepath, key, value, important)
        else:
            # when multiple aliases exist, default to the named key
            assert self.name in keys, "conda doctor should help here"
            key = self.name
            value, important = self.__extract[self.parameter_type](yaml_dict, key)
            return Match(filepath, key, value, important)

    @staticmethod
    def __merge_matches_single(matches):
        important_match = first(matches, lambda x: x.important, default=NO_MATCH)
        if important_match is not NO_MATCH:
            return important_match.value

        last_match = last(matches, lambda x: x is not NO_MATCH, default=NO_MATCH)
        if last_match is not NO_MATCH:
            return last_match.value

        raise ThisShouldNeverHappenError()

    @staticmethod
    def __merge_matches_list(matches):
        # get matches up to and including first important_match
        #  look for 0 in important, because 0 represents the key
        important_matches = cumfirst(matches, lambda x: 0 in x.important)

        # get individual lines from important_matches that were marked important
        # these will be prepended to the final result
        def get_important_lines(match):
            # get important line numbers, but subtract 1, because 0 is the key line
            line_numbers = (q-1 for q in match.important if q)
            return tuple(match.value[q] for q in line_numbers)
        important_lines = concat(get_important_lines(m) for m in important_matches)

        # reverse the matches and concat the lines
        #   reverse because elements closer to the end of search path that are not marked
        #   important take precedence
        catted_lines = concat(m.value for m in reversed(important_matches))

        # now important_lines + concatted_lines
        return tuple(unique(concatv(important_lines, catted_lines)))

    @staticmethod
    def __merge_matches_map(matches):
        # get matches up to and including first important_match
        #  look for 0 in important, because 0 represents the key
        important_matches = cumfirst(matches, lambda x: 0 in x.important)

        # mapkeys with important matches
        def get_important_mapkeys(match):
            return {q: match.value[q] for q in match.important if q}
        important_maps = (get_important_mapkeys(m) for m in important_matches)

        # dump all matches in a dict
        # then overwrite with important matches
        return merge(concatv((m.value for m in important_matches), reversed(important_maps)))

    __merge_matches = {
        ParameterType.single: __merge_matches_single.__func__,
        ParameterType.list: __merge_matches_list.__func__,
        ParameterType.map: __merge_matches_map.__func__,
    }

    def __get__(self, instance, instance_type):
        # strategy is "extract and merge," which is actually just map and reduce
        # extract matches from each source in SEARCH_PATH
        # then merge matches together

        # TODO: cache result on instance object

        matches = tuple(m for m in (self.__get_match(filepath, yaml_dict)
                                    for filepath, yaml_dict in iteritems(instance.raw_data))
                        if m is not NO_MATCH)

        if not matches:
            return self.default
        else:
            return self.__merge_matches[self.parameter_type](matches)


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
    track_features = Parameter((), parameter_type=ParameterType.list)
    channels = Parameter((), parameter_type=ParameterType.list)
    disallow = Parameter((), parameter_type=ParameterType.list)
    create_default_packages = Parameter((), parameter_type=ParameterType.list)
    envs_dirs = Parameter((), parameter_type=ParameterType.list)
    default_channels = Parameter((), parameter_type=ParameterType.list)
    proxy_servers = Parameter({}, parameter_type=ParameterType.map)


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
            # ssl_verify can be a boolean value or a filename string
            """),
        'track_features': dals("""
            """),
        'channels': dals("""
            """),
        'disallow': dals("""
            # set packages disallowed to be installed
            """),
        'create_default_packages': dals("""
            # packages which are added to a newly created environment by default
            """),
        'envs_dirs': dals("""
            """),
        'default_channels': dals("""
            """),
        'proxy_servers': dals("""
            """),
    }



if __name__ == "__main__":
    test_yaml_raw = {
        'file1': dals("""
            channels:
              - kalefranz
              - defaults  #!important
              - conda

            always_yes: no #!important

            proxy_servers:
                http: this-one #!important
                https: not-this-one
        """),
        'file2': dals("""
            channels:
              - r

            always_yes: yes #!important
            changeps1: no

            proxy_servers:
                http: not-this-one
                https: this-one
        """),
        'file3': dals("""
            channels: #!important
              - locked

            always_yes: yes

            proxy_servers: #!important
                s3: notreallyvalid
        """),
        'file4': dals("""
            proxy_servers:
                http: http://user:pass@corp.com:8080 #!important
                https: https://user:pass@corp.com:8080
        """),
    }

    import doctest
    doctest.testmod()

    test_yaml_12 = OrderedDict((f, yaml_load(test_yaml_raw[f])) for f in ('file1', 'file2'))
    config = Configuration(test_yaml_12)
    assert config.channels == ('defaults', 'r', 'kalefranz', 'conda')

    test_yaml_312 = OrderedDict((f, yaml_load(test_yaml_raw[f]))
                                for f in ('file3', 'file1', 'file2'))
    config = Configuration(test_yaml_312)
    assert config.channels == ('locked',), config.channels
    assert config.always_yes == False

    config = Configuration(load_raw_configs())
    assert config.always_yes is False
    assert config.show_channel_urls is None
    assert config.binstar_upload is None
    assert isinstance(config.track_features, tuple), config.track_features

    test_yaml_4 = OrderedDict((f, yaml_load(test_yaml_raw[f])) for f in ('file4', ))
    config = Configuration(test_yaml_4)
    # print(config.proxy_servers)
    # import pdb; pdb.set_trace()

