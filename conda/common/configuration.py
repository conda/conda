# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from abc import ABCMeta, abstractmethod
from collections import Mapping, Set, defaultdict
from enum import Enum
from glob import glob
from itertools import chain, takewhile
from logging import getLogger
from os import environ, stat
from os.path import join
from stat import S_IFDIR, S_IFMT, S_IFREG

try:
    from ruamel_yaml.comments import CommentedSeq, CommentedMap
except ImportError:  # pragma: no cover
    from ruamel.yaml.comments import CommentedSeq, CommentedMap  # pragma: no cover

try:
    from cytoolz.toolz.dicttoolz import merge
    from cytoolz.toolz.functoolz import excepts
    from cytoolz.toolz.itertoolz import concat, concatv, unique
except ImportError:
    from .._vendor.toolz.dicttoolz import merge
    from .._vendor.toolz.functoolz import excepts
    from .._vendor.toolz.itertoolz import concat, concatv, unique

from .compat import (isiterable, iteritems, itervalues, odict, primitive_types, text_type,
                     with_metaclass)
from .yaml import yaml_load
from .._vendor.auxlib.collection import first, frozendict, last
from .._vendor.auxlib.exceptions import Raise, ThisShouldNeverHappenError, ValidationError
from .._vendor.auxlib.path import expand
from .._vendor.auxlib.type_coercion import typify_data_structure
from ..base.constants import EMPTY_MAP
from ..exceptions import ValidationError as CondaValidationError

__all__ = ["Configuration", "ParameterFlag", "PrimitiveParameter",
           "SequenceParameter", "MapParameter"]

log = getLogger(__name__)


class MultiValidationError(CondaValidationError):

    def __init__(self, errors):
        messages = "\n".join(repr(e) for e in errors)
        super(MultiValidationError, self).__init__(messages)


class ParameterFlag(Enum):
    important = 'important'
    top = "top"
    bottom = "bottom"

    @classmethod
    def from_name(cls, name):
        return cls[name]

    @classmethod
    def from_value(cls, value):
        return cls(value)

    @classmethod
    def from_string(cls, string):
        try:
            string = string.strip('!#')
            return cls.from_value(string)
        except (ValueError, AttributeError):
            return None


def make_immutable(value):
    if isinstance(value, Mapping):
        return frozendict(value)
    elif isinstance(value, Set):
        return frozenset(value)
    elif isiterable(value):
        return tuple(value)
    else:
        return value


@with_metaclass(ABCMeta)
class RawParameter(object):

    def __init__(self, source, key, raw_value):
        self.source = source
        self.key = key
        self._raw_value = raw_value

    def __repr__(self):
        return text_type(vars(self))

    @abstractmethod
    def value(self, parameter_type):
        raise NotImplementedError()

    @abstractmethod
    def keyflag(self, parameter_type):
        raise NotImplementedError()

    @abstractmethod
    def valueflags(self, parameter_type):
        raise NotImplementedError()

    @classmethod
    def make_raw_parameters(cls, source, from_map):
        if from_map:
            return dict((key, cls(source, key, from_map[key])) for key in from_map)
        return EMPTY_MAP


class EnvRawParameter(RawParameter):
    source = 'envvars'

    def value(self, parameter_type):
        return self.__important_split_value[0].strip()

    def keyflag(self, parameter_type):
        return ParameterFlag.important if len(self.__important_split_value) >= 2 else None

    def valueflags(self, parameter_type):
        return None

    @property
    def __important_split_value(self):
        return self._raw_value.split("!important")

    @classmethod
    def make_raw_parameters(cls, appname):
        keystart = "{0}_".format(appname.upper())
        raw_env = dict((k.replace(keystart, '').lower(), v)
                       for k, v in iteritems(environ) if k.startswith(keystart))
        return super(EnvRawParameter, cls).make_raw_parameters(EnvRawParameter.source, raw_env)


class ArgParseRawParameter(RawParameter):
    source = 'cmd_line'

    def value(self, parameter_type):
        return make_immutable(self._raw_value)

    def keyflag(self, parameter_type):
        return None

    def valueflags(self, parameter_type):
        return None

    @classmethod
    def make_raw_parameters(cls, args_from_argparse):
        return super(ArgParseRawParameter, cls).make_raw_parameters(ArgParseRawParameter.source,
                                                                    vars(args_from_argparse))


class YamlRawParameter(RawParameter):
    # this class should encapsulate all direct use of ruamel.yaml in this module

    def __init__(self, source, key, raw_value, keycomment):
        self._keycomment = keycomment
        super(YamlRawParameter, self).__init__(source, key, raw_value)

    def value(self, parameter_type):
        self.__process(parameter_type)
        return self._value

    def keyflag(self, parameter_type):
        return ParameterFlag.from_string(self._keycomment)

    def valueflags(self, parameter_type):
        self.__process(parameter_type)
        return self._valueflags

    def __process(self, parameter_type):
        if hasattr(self, '_value'):
            return
        elif isinstance(self._raw_value, CommentedSeq):
            valuecomments = self._get_yaml_list_comments(self._raw_value)
            self._valueflags = tuple(ParameterFlag.from_string(s) for s in valuecomments)
            self._value = tuple(self._raw_value)
        elif isinstance(self._raw_value, CommentedMap):
            valuecomments = self._get_yaml_map_comments(self._raw_value)
            self._valueflags = dict((k, ParameterFlag.from_string(v))
                              for k, v in iteritems(valuecomments) if v is not None)
            self._value = frozendict(self._raw_value)
        elif isinstance(self._raw_value, primitive_types):
            self._valueflags = None
            self._value = self._raw_value
        else:
            raise ThisShouldNeverHappenError()  # pragma: no cover

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
    def make_raw_parameters(cls, source, from_map):
        if from_map:
            return dict((key, cls(source, key, from_map[key],
                                  cls._get_yaml_key_comment(from_map, key)))
                        for key in from_map)
        return EMPTY_MAP

    @classmethod
    def make_raw_parameters_from_file(cls, filepath):
        with open(filepath, 'r') as fh:
            ruamel_yaml = yaml_load(fh)
        return cls.make_raw_parameters(filepath, ruamel_yaml) or EMPTY_MAP


def load_file_configs(search_path):
    # returns an ordered map of filepath and dict of raw parameter objects

    def _file_yaml_loader(fullpath):
        assert fullpath.endswith(".yml") or fullpath.endswith("condarc"), fullpath
        yield fullpath, YamlRawParameter.make_raw_parameters_from_file(fullpath)

    def _dir_yaml_loader(fullpath):
        for filepath in glob(join(fullpath, "*.yml")):
            yield filepath, YamlRawParameter.make_raw_parameters_from_file(filepath)

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
    raw_data = odict(kv for kv in chain.from_iterable(load_paths))
    return raw_data


@with_metaclass(ABCMeta)
class Parameter(object):
    _type = None
    _element_type = None

    def __init__(self, default, aliases=(), validation=None):
        self._name = None
        self._names = None
        self.default = default
        self.aliases = aliases
        self._validation = validation

    def _set_name(self, name):
        # this is an explicit method, and not a descriptor/setter
        # it's meant to be called by the Configuration metaclass
        self._name = name
        self._names = frozenset(x for x in chain(self.aliases, (name, )))
        return name

    @property
    def name(self):
        if self._name is None:
            # The Configuration metaclass should call the `_set_name` method.
            raise ThisShouldNeverHappenError()  # pragma: no cover
        return self._name

    @property
    def names(self):
        if self._names is None:
            # The Configuration metaclass should call the `_set_name` method.
            raise ThisShouldNeverHappenError()  # pragma: no cover
        return self._names

    def _collect_single_raw_parameter(self, raw_parameters):
        # while supporting parameter name aliases, we enforce that one one definition is given
        # per data source
        keys = self.names & frozenset(raw_parameters.keys())
        numkeys = len(keys)
        if numkeys == 0:
            return None
        elif numkeys == 1:
            key, = keys  # get single key from frozenset
            return raw_parameters[key]
        else:
            raise CondaValidationError("Multiple aliased keys in file %s:%s"
                                       % (raw_parameters[next(iter(keys))].source,
                                          "\n  - ".join(chain.from_iterable((('',), keys)))))

    def _get_all_matches(self, instance):
        # a match is a single raw parameter instance
        return tuple(m for m in (self._collect_single_raw_parameter(raw_parameters)
                                 for filepath, raw_parameters in iteritems(instance.raw_data))
                     if m is not None)

    @abstractmethod
    def _merge(self, matches):
        raise NotImplementedError()  # pragma: no cover

    def __get__(self, instance, instance_type):
        # strategy is "extract and merge," which is actually just map and reduce
        # extract matches from each source in SEARCH_PATH
        # then merge matches together

        if self.name in instance._cache:
            return instance._cache[self.name]

        matches = self._get_all_matches(instance)
        result = typify_data_structure(self._merge(matches) if matches else self.default)
        self.validate(instance, result)
        instance._cache[self.name] = result
        return result

    def validate(self, instance, value):
        """Validate a Parameter value.

        Args:
            instance (Configuration): The instance object to which the Parameter descriptor is
                attached.
            value: The value to be validated.

        Returns:
            A valid value.

        Raises:
            ValidationError:
        """
        if (isinstance(value, self._type) and
                (self._validation is None or self._validation(value))):
            return value
        else:
            raise CondaValidationError(getattr(self, 'name', 'undefined name'), value)

    def _match_key_is_important(self, raw_parameter):
        return raw_parameter.keyflag(self.__class__) is ParameterFlag.important


class PrimitiveParameter(Parameter):
    """Parameter type for a Configuration class that holds a single python primitive value.

    The python primitive types are str, int, float, complex, bool, and NoneType. In addition,
    python 2 has long and unicode types.
    """

    def __init__(self, default, aliases=(), validation=None, parameter_type=None):
        """
        Args:
            default (Any):  The parameter's default value.
            aliases (Iterable[str]): Alternate names for the parameter.
            validation (callable): Given a parameter value as input, return a boolean indicating
                validity, or alternately return a string describing an invalid value.
            parameter_type (type or Tuple[type]): Type-validation of parameter's value. If None,
                type(default) is used.

        """
        self._type = type(default) if parameter_type is None else parameter_type
        self._element_type = self._type
        super(PrimitiveParameter, self).__init__(default, aliases, validation)

    def _merge(self, matches):
        important_match = first(matches, self._match_key_is_important, default=None)
        if important_match is not None:
            return important_match.value(self.__class__)

        last_match = last(matches, lambda x: x is not None, default=None)
        if last_match is not None:
            return last_match.value(self.__class__)
        raise ThisShouldNeverHappenError()  # pragma: no cover


class SequenceParameter(Parameter):
    """Parameter type for a Configuration class that holds a sequence (i.e. list) of python
    primitive values.
    """
    _type = tuple

    def __init__(self, element_type, default=(), aliases=(), validation=None):
        """
        Args:
            element_type (type or Iterable[type]): The generic type of each element in
                the sequence.
            default (Iterable[str]):  The parameter's default value.
            aliases (Iterable[str]): Alternate names for the parameter.
            validation (callable): Given a parameter value as input, return a boolean indicating
                validity, or alternately return a string describing an invalid value.

        """
        self._element_type = element_type
        super(SequenceParameter, self).__init__(default, aliases, validation)

    def validate(self, instance, value):
        et = self._element_type
        for el in value:
            if not isinstance(el, et):
                raise ValidationError(self.name, el, et)
        return super(SequenceParameter, self).validate(instance, value)

    def _merge(self, matches):
        # get matches up to and including first important_match
        #   but if no important_match, then all matches are important_matches
        important_matches = tuple(takewhile(self._match_key_is_important, matches)) or matches

        # get individual lines from important_matches that were marked important
        # these will be prepended to the final result
        def get_important_lines(match):
            return tuple(line
                         for line, flag in zip(match.value(self.__class__),
                                               match.valueflags(self.__class__))
                         if flag is ParameterFlag.important)
        important_lines = concat(get_important_lines(m) for m in important_matches)

        # reverse the matches and concat the lines
        #   reverse because elements closer to the end of search path that are not marked
        #   important take precedence
        catted_lines = concat(m.value(self.__class__) for m in reversed(important_matches))

        # now de-dupe important_lines + concatted_lines
        return tuple(unique(concatv(important_lines, catted_lines)))


class MapParameter(Parameter):
    """Parameter type for a Configuration class that holds a map (i.e. dict) of python
    primitive values.
    """
    _type = dict

    def __init__(self, element_type, default=None, aliases=(), validation=None):
        """
        Args:
            element_type (type or Iterable[type]): The generic type of each element.
            default (Mapping):  The parameter's default value. If None, will be an empty dict.
            aliases (Iterable[str]): Alternate names for the parameter.
            validation (callable): Given a parameter value as input, return a boolean indicating
                validity, or alternately return a string describing an invalid value.

        """
        self._element_type = element_type
        super(MapParameter, self).__init__(default or dict(), aliases, validation)

    def validate(self, instance, value):
        et = self._element_type
        [Raise(CondaValidationError(self.name, v, et))
         for v in itervalues(value) if not isinstance(v, et)]  # TODO: cleanup
        return super(MapParameter, self).validate(instance, value)

    def _merge(self, matches):
        # get matches up to and including first important_match
        #   but if no important_match, then all matches are important_matches
        relevant_matches = tuple(takewhile(self._match_key_is_important, matches)) or matches

        # mapkeys with important matches
        def key_is_important(match, key):
            return match.valueflags(self.__class__).get(key) is ParameterFlag.important
        important_maps = tuple(dict((k, v)
                                    for k, v in iteritems(match.value(self.__class__))
                                    if key_is_important(match, k))
                               for match in relevant_matches)

        # dump all matches in a dict
        # then overwrite with important matches
        return merge(concatv((m.value(self.__class__) for m in relevant_matches),
                             reversed(important_maps)))


class ConfigurationType(type):
    """metaclass for Configuration"""

    def __init__(cls, name, bases, attr):
        super(ConfigurationType, cls).__init__(name, bases, attr)

        # call _set_name for each
        cls.parameter_names = tuple(p._set_name(name) for name, p in iteritems(cls.__dict__)
                                    if isinstance(p, Parameter))


@with_metaclass(ConfigurationType)
class Configuration(object):

    def __init__(self, search_path=(), app_name=None, argparse_args=None):
        self.raw_data = odict()
        self._cache = dict()
        self._validation_errors = defaultdict(list)
        if search_path:
            self._add_search_path(search_path)
        if app_name is not None:
            self._add_env_vars(app_name)
        if argparse_args is not None:
            self._add_argparse_args(argparse_args)

    def _add_search_path(self, search_path):
        return self._add_raw_data(load_file_configs(search_path))

    def _add_env_vars(self, app_name):
        self.raw_data[EnvRawParameter.source] = EnvRawParameter.make_raw_parameters(app_name)
        self._cache = dict()
        return self

    def _add_argparse_args(self, argparse_args):
        self._argparse_args = argparse_args
        source = ArgParseRawParameter.source
        self.raw_data[source] = ArgParseRawParameter.make_raw_parameters(self._argparse_args)
        self._cache = dict()
        return self

    def _add_raw_data(self, raw_data):
        self.raw_data.update(raw_data)
        self._cache = dict()
        return self

    # def dump(self):
    #     Match = namedtuple('Match', ('filepath', 'key', 'raw_parameter'))

    def validate_all(self):
        validation_errors = defaultdict(list)
        for key in self.parameter_names:
            parameter = self.__class__.__dict__[key]
            for match in parameter._get_all_matches(self):
                try:
                    result = typify_data_structure(match.value(parameter.__class__))
                    parameter.validate(self, result)
                except ValidationError as e:
                    validation_errors[key].append(e)

        if validation_errors:
            raise MultiValidationError(validation_errors)
