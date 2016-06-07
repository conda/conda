# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

from collections import OrderedDict, namedtuple
from glob import glob
from itertools import chain, takewhile
from logging import getLogger
from os import environ, stat
from os.path import join
from stat import S_IFREG, S_IFDIR, S_IFMT

from auxlib.collection import first, last, call_each, firstitem
from auxlib.compat import (iteritems, with_metaclass, itervalues, string_types,
                           primitive_types, text_type, odict)
from auxlib.exceptions import ThisShouldNeverHappenError, ValidationError, Raise
from auxlib.path import expand
from auxlib.type_coercion import typify
from enum import Enum
from toolz.dicttoolz import merge
from toolz.functoolz import excepts
from toolz.itertoolz import concat, unique, concatv

from .yaml import yaml_load


from ruamel.yaml.comments import CommentedSeq, CommentedMap


log = getLogger(__name__)


Match = namedtuple('Match', ('filepath', 'key', 'raw_parameter'))
NO_MATCH = Match(None, None, None)


class ParameterType(Enum):
    primitive = 'primitive'
    sequence = 'sequence'
    map = 'map'


class ParameterFlag(Enum):
    important = 'important'

    @classmethod
    def from_string(cls, string):
        if string and 'important' in string:
            return cls.important
        return None


class RawParameter(object):

    def __init__(self, key, value, parameter_type, keyflag=None, valueflags=None):
        self.key = key
        self.value = value
        self.parameter_type = parameter_type
        self.keyflag = keyflag
        self.valueflags = valueflags

    def __repr__(self):
        return text_type(vars(self))

    @classmethod
    def make_raw_parameters(cls, from_map):
        return dict((key, cls(from_map, key)) for key in from_map)


class EnvRawParameter(RawParameter):

    def __init__(self, groomed_env, key):
        self.key = key
        raw_value = groomed_env[key]
        important_split_value = raw_value.split("!important")
        keyflag = ParameterFlag.important if len(important_split_value) >= 2 else None
        value = typify(important_split_value[0].strip())
        parameter_type = ParameterType.primitive
        valueflags = None
        super(EnvRawParameter, self).__init__(key, value, parameter_type, keyflag, valueflags)

    @classmethod
    def make_raw_parameters(cls, appname):
        keystart = "{0}_".format(appname.upper())
        raw_env = dict((k.replace(keystart, '').lower(), v)
                       for k, v in iteritems(environ) if k.startswith(keystart))
        return super(EnvRawParameter, cls).make_raw_parameters(raw_env)


class YamlRawParameter(RawParameter):
    # this class should all direct use of ruamel.yaml in this module

    def __init__(self, ruamel_yaml_object, key):
        rawvalue = ruamel_yaml_object[key]
        keycomment = self._get_yaml_key_comment(ruamel_yaml_object, key)
        keyflag = ParameterFlag.from_string(keycomment)
        if isinstance(rawvalue, CommentedSeq):
            valuecomments = self._get_yaml_list_comments(rawvalue)
            valueflags = tuple(ParameterFlag.from_string(s) for s in valuecomments)
            parameter_type = ParameterType.sequence
            value = tuple(rawvalue)
        elif isinstance(rawvalue, CommentedMap):
            valuecomments = self._get_yaml_map_comments(rawvalue)
            valueflags = dict((k, ParameterFlag.from_string(v))
                              for k, v in iteritems(valuecomments) if v is not None)
            parameter_type = ParameterType.map
            value = dict(rawvalue)
        elif isinstance(rawvalue, primitive_types):
            valueflags = None
            value = rawvalue
            parameter_type = ParameterType.primitive
        else:
            raise ThisShouldNeverHappenError()
        super(YamlRawParameter, self).__init__(key, value, parameter_type, keyflag, valueflags)

    @staticmethod
    def _get_yaml_key_comment(commented_dict, key):
        try:
            return commented_dict.ca.items[key][2].value.strip()
        except (AttributeError, KeyError):
            return None

    @staticmethod
    def _get_yaml_list_comments(value):
        items = value.ca.items
        raw_comment_lines = tuple(excepts((AttributeError, KeyError, TypeError),
                                          lambda q: items.get(q)[0].value.strip() or None,
                                          lambda _: None  # default value on exception
                                          )(q)
                                  for q in range(len(value)))
        return raw_comment_lines

    @staticmethod
    def _get_yaml_map_comments(rawvalue):
        return dict((key, excepts(AttributeError,
                                  lambda k: first(k.ca.items.values())[2].value.strip() or None,
                                  lambda _: None  # default value on exception
                                  )(key))
                    for key in rawvalue)

    @classmethod
    def make_raw_parameters_from_file(cls, filepath):
        with open(filepath, 'r') as fh:
            ruamel_yaml = yaml_load(fh)
        return cls.make_raw_parameters(ruamel_yaml)


def load_raw_configs(search_path):
    # returns an ordered map of filepath and raw yaml dict

    def _file_yaml_loader(fullpath):
        assert fullpath.endswith(".yml") or fullpath.endswith("condarc"), fullpath
        yield fullpath, YamlRawParameter.make_raw_parameters_from_file(fullpath)

    def _dir_yaml_loader(fullpath):
        for filepath in glob(join(fullpath, "*.yml")):
            assert fullpath.endswith(".yml") or fullpath.endswith("condarc"), fullpath
            yield filepath, YamlRawParameter.make_raw_parameters_from_file(fullpath)

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


class Parameter(object):
    _parameter_interface = None
    _parameter_type = None

    def __init__(self, default, aliases=(), validation=None):
        self._name = None
        self._names = None
        self.default = default
        self.aliases = aliases
        self._validation = validation

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

    def _get_match(self, filepath, raw_parameters):
        # TODO: cleanup
        keys = self.names & raw_parameters.keys()
        numkeys = len(keys)
        if numkeys == 0:
            return NO_MATCH
        elif numkeys == 1:
            key = keys.pop()
            return Match(filepath, key, raw_parameters[key])
        else:
            # when multiple aliases exist, default to the named key
            assert self.name in keys, "conda doctor should help here"
            key = self.name
            return Match(filepath, key, raw_parameters[key])

    @staticmethod
    def _merge(matches):
        raise NotImplementedError()

    def __get__(self, instance, instance_type):
        # strategy is "extract and merge," which is actually just map and reduce
        # extract matches from each source in SEARCH_PATH
        # then merge matches together

        # TODO: cache result on instance object

        matches = tuple(m for m in (self._get_match(filepath, raw_parameters)
                                    for filepath, raw_parameters in iteritems(instance.raw_data))
                        if m is not NO_MATCH)
        if not matches:
            return self.default
        else:
            merged = self._merge(matches)
            return self.validate(instance, merged)

    def validate(self, instance, val):
        if (isinstance(val, self._parameter_type) and
                (self._validation is None or self._validation(val))):
            return val
        else:
            raise ValidationError(getattr(self, 'name', 'undefined name'), val)

    @staticmethod
    def _match_key_is_important(match):
        return match.raw_parameter.keyflag is ParameterFlag.important


class PrimitiveParameter(Parameter):

    def __init__(self, default, aliases=(), validation=None, parameter_type=None):
        self._parameter_type = type(default) if parameter_type is None else parameter_type
        super(PrimitiveParameter, self).__init__(default, aliases, validation)

    @staticmethod
    def _merge(matches):
        important_match = first(matches, Parameter._match_key_is_important, default=NO_MATCH)
        if important_match is not NO_MATCH:
            return typify(important_match.raw_parameter.value)

        last_match = last(matches, lambda x: x is not NO_MATCH, default=NO_MATCH)
        if last_match is not NO_MATCH:
            return typify(last_match.raw_parameter.value)

        raise ThisShouldNeverHappenError()


class SequenceParameter(Parameter):
    _parameter_type = tuple

    def __init__(self, element_type, default=(), aliases=(), validation=None):
        self._element_type = element_type
        super(SequenceParameter, self).__init__(default, aliases, validation)

    def validate(self, instance, val):
        et = self._element_type
        for el in val:
            if not isinstance(el, et):
                raise ValidationError(self.name, el, et)
        return super(SequenceParameter, self).validate(instance, val)

    @staticmethod
    def _merge(matches):
        # get matches up to and including first important_match
        #   but if no important_match, then all matches are important_matches
        important_matches = tuple(takewhile(Parameter._match_key_is_important, matches)) or matches

        # get individual lines from important_matches that were marked important
        # these will be prepended to the final result
        def get_important_lines(match):
            rp = match.raw_parameter
            return tuple(line for line, flag in zip(rp.value, rp.valueflags)
                         if flag is ParameterFlag.important)
        important_lines = concat(get_important_lines(m) for m in important_matches)

        # reverse the matches and concat the lines
        #   reverse because elements closer to the end of search path that are not marked
        #   important take precedence
        catted_lines = concat(m.raw_parameter.value for m in reversed(important_matches))

        # now de-dupe important_lines + concatted_lines
        return tuple(unique(concatv(important_lines, catted_lines)))


class MapParameter(Parameter):
    _parameter_type = dict

    def __init__(self, element_type, default=None, aliases=(), validation=None):
        self._element_type = element_type
        super(MapParameter, self).__init__(default or dict(), aliases, validation)

    def validate(self, instance, val):
        et = self._element_type
        call_each(Raise(ValidationError(self.name, v, et))
                  for v in itervalues(val) if not isinstance(v, et))
        return super(MapParameter, self).validate(instance, val)

    @staticmethod
    def _merge(matches):
        # get matches up to and including first important_match
        #   but if no important_match, then all matches are important_matches
        important_matches = tuple(takewhile(Parameter._match_key_is_important, matches)) or matches

        # mapkeys with important matches
        def get_important_mapkeys(match):
            rp = match.raw_parameter
            return dict((k, rp.value[k]) for k in rp.value
                        if rp.valueflags.get(k) is ParameterFlag.important)
        important_maps = tuple(get_important_mapkeys(m) for m in important_matches)

        # dump all matches in a dict
        # then overwrite with important matches
        return merge(concatv((m.raw_parameter.value for m in important_matches),
                             reversed(important_maps)))


class ConfigurationType(type):

    def __init__(cls, name, bases, attr):
        super(ConfigurationType, cls).__init__(name, bases, attr)
        any(field.set_name(name)
            for name, field in iteritems(cls.__dict__)
            if isinstance(field, Parameter))


@with_metaclass(ConfigurationType)
class Configuration(object):

    def __init__(self, raw_data=None, app_name=None):
        self.raw_data = raw_data or odict()
        if app_name is not None:
            self.raw_data['envvars'] = EnvRawParameter.make_raw_parameters(app_name)

    @classmethod
    def from_search_path(cls, search_path):
        return cls(load_raw_configs(search_path))


if __name__ == "__main__":
    from auxlib.ish import dals
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
              s3: only-this-one
        """),
        'file4': dals("""
            proxy_servers:
              http: http://user:pass@corp.com:8080  #!important
              https: https://user:pass@corp.com:8080
        """),
    }


    class AppConfiguration(Configuration):
        channels = SequenceParameter(string_types)
        always_yes = PrimitiveParameter(False)
        proxy_servers = MapParameter(string_types)
        changeps1 = PrimitiveParameter(True)


    import doctest
    doctest.testmod()

    def load_from_above(*seq):
        return OrderedDict((f, YamlRawParameter.make_raw_parameters(yaml_load(test_yaml_raw[f])))
                           for f in seq)

    test_yaml_12 = load_from_above('file1', 'file2')
    config = AppConfiguration(test_yaml_12)
    assert config.changeps1 is False
    assert config.channels == ('defaults', 'r', 'kalefranz', 'conda'), config.channels

    test_yaml_312 = load_from_above('file3', 'file1', 'file2')
    config = AppConfiguration(test_yaml_312)
    assert config.channels == ('locked',), config.channels
    assert config.always_yes is False

    # config = AppConfiguration(load_raw_configs())
    # assert config.always_yes is False
    # assert config.show_channel_urls is None
    # assert config.binstar_upload is None
    # assert isinstance(config.track_features, tuple), config.track_features

    test_yaml_4 = load_from_above('file4',)
    config = AppConfiguration(test_yaml_4)
    assert config.proxy_servers == {'http': 'http://user:pass@corp.com:8080',
                                    'https': 'https://user:pass@corp.com:8080'}

    load_raw_configs(['~/.condarc'])

    import os
    appname = "myapp"
    os.environ["{0}_{1}".format(appname.upper(), 'always_yes'.upper())] = 'yes'
    config = AppConfiguration(app_name=appname)
    assert config.always_yes is True, config.always_yes

