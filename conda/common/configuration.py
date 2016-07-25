# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from abc import ABCMeta, abstractmethod
from collections import defaultdict, namedtuple, Mapping, Set
from enum import Enum
from glob import glob
from itertools import chain, takewhile
from logging import getLogger
from os import environ, stat
from os.path import join
from stat import S_IFREG, S_IFDIR, S_IFMT

from conda.base.constants import EMPTY_MAP
from .compat import (iteritems, with_metaclass, itervalues, primitive_types,
                     text_type, odict, isiterable)
from .yaml import yaml_load
from .._vendor.auxlib.collection import first, last, frozendict
from .._vendor.auxlib.exceptions import ThisShouldNeverHappenError, ValidationError, Raise
from .._vendor.auxlib.path import expand
from .._vendor.auxlib.type_coercion import typify_data_structure
from .._vendor.toolz.dicttoolz import merge
from .._vendor.toolz.functoolz import excepts
from .._vendor.toolz.itertoolz import concat, unique, concatv

try:
    from ruamel_yaml.comments import CommentedSeq, CommentedMap
except ImportError:  # pragma: no cover
    from ruamel.yaml.comments import CommentedSeq, CommentedMap  # pragma: no cover


__all__ = ["Configuration", "ParameterFlag", "PrimitiveParameter",
           "SequenceParameter", "MapParameter"]

log = getLogger(__name__)


Match = namedtuple('Match', ('filepath', 'key', 'raw_parameter', 'typed_value', 'typing_error'))
NO_MATCH = Match(None, None, None, None, None)


class MultiValidationError(ValidationError):

    def __init__(self, errors):
        messages = "\n".join(repr(e) for e in errors)
        super(MultiValidationError, self).__init__(None, msg=messages)


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

    def __init__(self, key, value, keyflag=None, valueflags=None):
        self.key = key
        self.value = make_immutable(value)
        self.keyflag = keyflag
        self.valueflags = valueflags

    def __repr__(self):
        return text_type(vars(self))

    @classmethod
    def make_raw_parameters(cls, from_map):
        if from_map:
            return dict((key, cls(from_map, key)) for key in from_map)
        return EMPTY_MAP


class EnvRawParameter(RawParameter):

    def __init__(self, groomed_env, key):
        self.key = key
        raw_value = groomed_env[key]
        important_split_value = raw_value.split("!important")
        keyflag = ParameterFlag.important if len(important_split_value) >= 2 else None
        value = important_split_value[0].strip()
        valueflags = None
        super(EnvRawParameter, self).__init__(key, value, keyflag, valueflags)

    @classmethod
    def make_raw_parameters(cls, appname):
        keystart = "{0}_".format(appname.upper())
        raw_env = dict((k.replace(keystart, '').lower(), v)
                       for k, v in iteritems(environ) if k.startswith(keystart))
        return super(EnvRawParameter, cls).make_raw_parameters(raw_env)


class ArgParseRawParameter(RawParameter):

    def __init__(self, args_from_argparse, key):
        self.key = key
        raw_value = args_from_argparse[key]
        super(ArgParseRawParameter, self).__init__(key, raw_value, None, None)

    @classmethod
    def make_raw_parameters(cls, args_from_argparse):
        return super(ArgParseRawParameter, cls).make_raw_parameters(vars(args_from_argparse))


class YamlRawParameter(RawParameter):
    # this class should encapsulate all direct use of ruamel.yaml in this module

    def __init__(self, ruamel_yaml_object, key):
        rawvalue = ruamel_yaml_object[key]
        keycomment = self._get_yaml_key_comment(ruamel_yaml_object, key)
        keyflag = ParameterFlag.from_string(keycomment)
        if isinstance(rawvalue, CommentedSeq):
            valuecomments = self._get_yaml_list_comments(rawvalue)
            valueflags = tuple(ParameterFlag.from_string(s) for s in valuecomments)
            value = tuple(rawvalue)
        elif isinstance(rawvalue, CommentedMap):
            valuecomments = self._get_yaml_map_comments(rawvalue)
            valueflags = dict((k, ParameterFlag.from_string(v))
                              for k, v in iteritems(valuecomments) if v is not None)
            value = dict(rawvalue)
        elif isinstance(rawvalue, primitive_types):
            valueflags = None
            value = rawvalue
        else:
            raise ThisShouldNeverHappenError()  # pragma: no cover
        super(YamlRawParameter, self).__init__(key, value, keyflag, valueflags)

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
    # returns an ordered map of filepath and dict of raw parameter objects

    def _file_yaml_loader(fullpath):
        assert fullpath.endswith(".yml") or fullpath.endswith("condarc"), fullpath
        yield fullpath, YamlRawParameter.make_raw_parameters_from_file(fullpath)

    def _dir_yaml_loader(fullpath):
        for filepath in glob(join(fullpath, "*.yml")):
            assert filepath.endswith(".yml") or filepath.endswith("condarc"), filepath
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

    def _pull_match_from_single_raw(self, raw_parameters, filepath):
        keys = self.names & frozenset(raw_parameters.keys())
        numkeys = len(keys)
        if numkeys == 0:
            return NO_MATCH
        elif numkeys == 1:
            key, = keys
            raw_value = raw_parameters[key]
            try:
                typed_value = typify_data_structure(raw_value.value, self._element_type)
                return Match(filepath, key, raw_value, typed_value, None)
            except ValueError as e:
                # from typify
                return Match(filepath, key, raw_value, None, e)
        else:
            return Match(filepath, self.name, keys, None,
                         ValidationError(self.name, msg="Multiple aliased keys in file {0}:\n"
                                                        "  - {1}".format(filepath,
                                                                         "\n  - ".join(keys))))

    def _get_all_matches(self, instance):
        return tuple(m for m in (self._pull_match_from_single_raw(raw_parameters, filepath)
                                 for filepath, raw_parameters in iteritems(instance.raw_data))
                     if m is not NO_MATCH)

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
        typing_errors = tuple(m.typing_error for m in matches if m.typing_error is not None)
        if typing_errors:
            raise MultiValidationError(typing_errors)
        elif matches:
            result = self._merge(matches)
        else:
            result = self.default
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
            raise ValidationError(getattr(self, 'name', 'undefined name'), value)

    @staticmethod
    def _match_key_is_important(match):
        return match.raw_parameter.keyflag is ParameterFlag.important


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
        important_match = first(matches, Parameter._match_key_is_important, default=NO_MATCH)
        if important_match is not NO_MATCH:
            return important_match.typed_value

        last_match = last(matches, lambda x: x is not NO_MATCH, default=NO_MATCH)
        if last_match is not NO_MATCH:
            return last_match.typed_value

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
        important_matches = tuple(takewhile(Parameter._match_key_is_important, matches)) or matches

        # get individual lines from important_matches that were marked important
        # these will be prepended to the final result
        def get_important_lines(match):
            return tuple(line
                         for line, flag in zip(match.typed_value, match.raw_parameter.valueflags)
                         if flag is ParameterFlag.important)
        important_lines = concat(get_important_lines(m) for m in important_matches)

        # reverse the matches and concat the lines
        #   reverse because elements closer to the end of search path that are not marked
        #   important take precedence
        catted_lines = concat(m.typed_value for m in reversed(important_matches))

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
        [Raise(ValidationError(self.name, v, et))
         for v in itervalues(value) if not isinstance(v, et)]  # TODO: cleanup
        return super(MapParameter, self).validate(instance, value)

    def _merge(self, matches):
        # get matches up to and including first important_match
        #   but if no important_match, then all matches are important_matches
        relevant_matches = tuple(takewhile(Parameter._match_key_is_important, matches)) or matches

        # # typify values
        # relevant_maps = tuple(dict((k, v) for k, v in iteritems(m.typed_value))
        #                       for m in relevant_matches)

        # mapkeys with important matches
        def key_is_important(match, key):
            return match.raw_parameter.valueflags.get(key) is ParameterFlag.important
        important_maps = tuple(dict((k, v)
                                    for k, v in iteritems(match.typed_value)
                                    if key_is_important(match, k))
                               for match in relevant_matches)

        # dump all matches in a dict
        # then overwrite with important matches
        return merge(concatv((m.typed_value for m in relevant_matches), reversed(important_maps)))


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
        self.raw_data.update(load_raw_configs(search_path))
        self._cache = dict()
        return self

    def _add_env_vars(self, app_name):
        self.raw_data['envvars'] = EnvRawParameter.make_raw_parameters(app_name)
        self._cache = dict()
        return self

    def _add_argparse_args(self, argparse_args):
        self._argparse_args = argparse_args
        self.raw_data['cmd_line'] = ArgParseRawParameter.make_raw_parameters(self._argparse_args)
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

            matches = parameter._get_all_matches(self)
            typing_errors = [m.typing_error for m in matches if m.typing_error is not None]

            # if there are any typing errors, it's game over for this key
            if typing_errors:
                validation_errors[key] = typing_errors
                continue

            for match in matches:
                try:
                    parameter.validate(self, match.typed_value)
                except ValidationError as e:
                    validation_errors[key].append(e)

        if validation_errors:
            raise MultiValidationError(validation_errors)

        # for filepath, raw_parameters in iteritems(self.raw_data):
        #     try:
        #         match = parameter._pull_match_from_single_raw(raw_parameters, filepath)
        #     except ValidationError as e:
        #         self._validation_errors[match] = ""
        #         print("The parameter '{0}' has invalid value '{1}' in {2}.\n{3}"
        #               .format(key, raw_parameters[key].value, filepath, text_type(e)))
        #         continue
        #     if match is NO_MATCH:
        #         continue
        #     v = parameter.validate(self, match.typed_value)
        #     if v is not True:
        #         msg = ("The parameter '{0}' has invalid value '{1}' in {2}."
        #                .format(match.key, match.raw_parameter.value, match.filepath))
        #         if isinstance(v, string_types):
        #             msg += "\n{0}".format(v)
        #         print(msg)
