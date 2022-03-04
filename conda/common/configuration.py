# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
A generalized application configuration utility.

Features include:
  - lazy eval
  - merges configuration files
  - parameter type validation, with custom validation
  - parameter aliases

Easily extensible to other source formats, e.g. json and ini

"""
from __future__ import absolute_import, division, print_function, unicode_literals

from abc import ABCMeta, abstractmethod
from collections import defaultdict
try:
    from collections.abc import Mapping
except ImportError:
    from collections import Mapping
import copy
from enum import Enum, EnumMeta
from itertools import chain
from logging import getLogger
from os import environ, stat
from os.path import basename, expandvars
from stat import S_IFDIR, S_IFMT, S_IFREG
import sys

from .compat import (binary_type, isiterable, iteritems, itervalues, odict, primitive_types,
                     scandir, string_types, text_type)
from .constants import NULL
from .path import expand
from .serialize import yaml_round_trip_load
from .. import CondaError, CondaMultiError
from ..auxlib.collection import AttrDict, first, last, make_immutable
from ..auxlib.exceptions import ThisShouldNeverHappenError
from ..auxlib.type_coercion import TypeCoercionError, typify, typify_data_structure
from .._vendor.frozendict import frozendict
from .._vendor.boltons.setutils import IndexedSet
from .._vendor.toolz import concat, concatv, excepts, merge, merge_with, unique

try:  # pragma: no cover
    from ruamel_yaml.comments import CommentedSeq, CommentedMap
    from ruamel_yaml.reader import ReaderError
    from ruamel_yaml.scanner import ScannerError
except ImportError:  # pragma: no cover
    from ruamel.yaml.comments import CommentedSeq, CommentedMap  # pragma: no cover
    from ruamel.yaml.reader import ReaderError
    from ruamel.yaml.scanner import ScannerError

log = getLogger(__name__)

EMPTY_MAP = frozendict()


def pretty_list(iterable, padding='  '):  # TODO: move elsewhere in conda.common
    if not isiterable(iterable):
        iterable = [iterable]
    try:
        return '\n'.join("%s- %s" % (padding, item) for item in iterable)
    except TypeError:
        return pretty_list([iterable], padding)


def pretty_map(dictionary, padding='  '):
    return '\n'.join("%s%s: %s" % (padding, key, value) for key, value in iteritems(dictionary))


def expand_environment_variables(unexpanded):
    if isinstance(unexpanded, string_types) or isinstance(unexpanded, binary_type):
        return expandvars(unexpanded)
    else:
        return unexpanded

class ConfigurationError(CondaError):
    pass


class ConfigurationLoadError(ConfigurationError):
    def __init__(self, path, message_addition='', **kwargs):
        message = "Unable to load configuration file.\n  path: %(path)s\n"
        super(ConfigurationLoadError, self).__init__(message + message_addition, path=path,
                                                     **kwargs)


class ValidationError(ConfigurationError):

    def __init__(self, parameter_name, parameter_value, source, msg=None, **kwargs):
        self.parameter_name = parameter_name
        self.parameter_value = parameter_value
        self.source = source
        super(ValidationError, self).__init__(msg, **kwargs)


class MultipleKeysError(ValidationError):

    def __init__(self, source, keys, preferred_key):
        self.source = source
        self.keys = keys
        msg = ("Multiple aliased keys in file %s:\n"
               "%s"
               "Must declare only one. Prefer '%s'" % (source, pretty_list(keys), preferred_key))
        super(MultipleKeysError, self).__init__(preferred_key, None, source, msg=msg)


class InvalidTypeError(ValidationError):
    def __init__(self, parameter_name, parameter_value, source, wrong_type, valid_types, msg=None):
        self.wrong_type = wrong_type
        self.valid_types = valid_types
        if msg is None:
            msg = ("Parameter %s = %r declared in %s has type %s.\n"
                   "Valid types:\n%s" % (parameter_name, parameter_value,
                                         source, wrong_type, pretty_list(valid_types)))
        super(InvalidTypeError, self).__init__(parameter_name, parameter_value, source, msg=msg)


class InvalidElementTypeError(InvalidTypeError):
    def __init__(self, parameter_name, parameter_value, source, wrong_type,
                 valid_types, index_or_key):
        qualifier = "at index" if isinstance(index_or_key, int) else "for key"
        msg = ("Parameter %s declared in %s has invalid element %r %s %s.\n"
               "Valid element types:\n"
               "%s." % (parameter_name, source, parameter_value, qualifier,
                        index_or_key, pretty_list(valid_types)))
        super(InvalidElementTypeError, self).__init__(parameter_name, parameter_value, source,
                                                      wrong_type, valid_types, msg=msg)


class CustomValidationError(ValidationError):
    def __init__(self, parameter_name, parameter_value, source, custom_message):
        msg = ("Parameter %s = %r declared in %s is invalid.\n"
               "%s" % (parameter_name, parameter_value, source, custom_message))
        super(CustomValidationError, self).__init__(parameter_name, parameter_value, source,
                                                    msg=msg)


class MultiValidationError(CondaMultiError, ConfigurationError):
    def __init__(self, errors, *args, **kwargs):
        super(MultiValidationError, self).__init__(errors, *args, **kwargs)


def raise_errors(errors):
    if not errors:
        return True
    elif len(errors) == 1:
        raise errors[0]
    else:
        raise MultiValidationError(errors)


class ParameterFlag(Enum):
    final = "final"
    top = "top"
    bottom = "bottom"

    def __str__(self):
        return "%s" % self.value

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


class RawParameter(metaclass=ABCMeta):

    def __init__(self, source, key, raw_value):
        self.source = source
        self.key = key
        try:
            # ignore flake8 on this because it finds an error on py3 even though it is guarded
            self._raw_value = unicode(raw_value.decode('utf-8'))  # NOQA
        except:
            self._raw_value = raw_value

    def __repr__(self):
        return text_type(vars(self))

    @abstractmethod
    def value(self, parameter_obj):
        raise NotImplementedError()

    @abstractmethod
    def keyflag(self):
        raise NotImplementedError()

    @abstractmethod
    def valueflags(self, parameter_obj):
        raise NotImplementedError()

    @classmethod
    def make_raw_parameters(cls, source, from_map):
        if from_map:
            return dict((key, cls(source, key, from_map[key])) for key in from_map)
        return EMPTY_MAP


class EnvRawParameter(RawParameter):
    source = 'envvars'

    def value(self, parameter_obj):
        # note: this assumes that EnvRawParameters will only have flat configuration of either
        # primitive or sequential type
        if hasattr(parameter_obj, 'string_delimiter'):
            assert isinstance(self._raw_value, string_types)
            string_delimiter = getattr(parameter_obj, 'string_delimiter')
            # TODO: add stripping of !important, !top, and !bottom
            return tuple(EnvRawParameter(EnvRawParameter.source, self.key, v)
                         for v in (vv.strip() for vv in self._raw_value.split(string_delimiter))
                         if v)
        else:
            return self.__important_split_value[0].strip()

    def keyflag(self):
        return ParameterFlag.final if len(self.__important_split_value) >= 2 else None

    def valueflags(self, parameter_obj):
        if hasattr(parameter_obj, 'string_delimiter'):
            string_delimiter = getattr(parameter_obj, 'string_delimiter')
            # TODO: add stripping of !important, !top, and !bottom
            return tuple('' for _ in self._raw_value.split(string_delimiter))
        else:
            return self.__important_split_value[0].strip()

    @property
    def __important_split_value(self):
        return self._raw_value.split("!important")

    @classmethod
    def make_raw_parameters(cls, appname):
        keystart = "{0}_".format(appname.upper())
        raw_env = dict((k.replace(keystart, '', 1).lower(), v)
                       for k, v in iteritems(environ) if k.startswith(keystart))
        return super(EnvRawParameter, cls).make_raw_parameters(EnvRawParameter.source, raw_env)


class ArgParseRawParameter(RawParameter):
    source = 'cmd_line'

    def value(self, parameter_obj):
        # note: this assumes ArgParseRawParameter will only have flat configuration of either
        # primitive or sequential type
        if isiterable(self._raw_value):
            children_values = []
            for i in range(len(self._raw_value)):
                children_values.append(ArgParseRawParameter(
                    self.source, self.key, self._raw_value[i]))
            return tuple(children_values)
        else:
            return make_immutable(self._raw_value)

    def keyflag(self):
        return None

    def valueflags(self, parameter_obj):
        return None if isinstance(parameter_obj, PrimitiveLoadedParameter) else ()

    @classmethod
    def make_raw_parameters(cls, args_from_argparse):
        return super(ArgParseRawParameter, cls).make_raw_parameters(ArgParseRawParameter.source,
                                                                    args_from_argparse)


class YamlRawParameter(RawParameter):
    # this class should encapsulate all direct use of ruamel.yaml in this module

    def __init__(self, source, key, raw_value, key_comment):
        self._key_comment = key_comment
        super(YamlRawParameter, self).__init__(source, key, raw_value)

        if isinstance(self._raw_value, CommentedSeq):
            value_comments = self._get_yaml_list_comments(self._raw_value)
            self._value_flags = tuple(ParameterFlag.from_string(s) for s in value_comments)
            children_values = []
            for i in range(len(self._raw_value)):
                children_values.append(YamlRawParameter(
                    self.source, self.key, self._raw_value[i], value_comments[i]))
            self._value = tuple(children_values)
        elif isinstance(self._raw_value, CommentedMap):
            value_comments = self._get_yaml_map_comments(self._raw_value)
            self._value_flags = dict((k, ParameterFlag.from_string(v))
                                     for k, v in iteritems(value_comments) if v is not None)
            children_values = {}
            for k, v in self._raw_value.items():
                children_values[k] = YamlRawParameter(self.source, self.key, v, value_comments[k])
            self._value = frozendict(children_values)
        elif isinstance(self._raw_value, primitive_types):
            self._value_flags = None
            self._value = self._raw_value
        else:
            print(type(self._raw_value), self._raw_value, file=sys.stderr)
            raise ThisShouldNeverHappenError()  # pragma: no cover

    def value(self, parameter_obj):
        return self._value

    def keyflag(self):
        return ParameterFlag.from_string(self._key_comment)

    def valueflags(self, parameter_obj):
        return self._value_flags

    @staticmethod
    def _get_yaml_key_comment(commented_dict, key):
        try:
            return commented_dict.ca.items[key][2].value.strip()
        except (AttributeError, KeyError):
            return None

    @staticmethod
    def _get_yaml_list_comments(value):
        items = value.ca.items
        raw_comment_lines = tuple(excepts((AttributeError, IndexError, KeyError, TypeError),
                                          lambda q: YamlRawParameter._get_yaml_list_comment_item(
                                              items[q]),
                                          lambda _: None  # default value on exception
                                          )(q)
                                  for q in range(len(value)))
        return raw_comment_lines

    @staticmethod
    def _get_yaml_list_comment_item(item):
        # take the pre_item comment if available
        # if not, take the first post_item comment if available
        if item[0]:
            return item[0].value.strip() or None
        else:
            return item[1][0].value.strip() or None

    @staticmethod
    def _get_yaml_map_comments(value):
        return dict((key, excepts((AttributeError, KeyError),
                                  lambda k: value.ca.items[k][2].value.strip() or None,
                                  lambda _: None  # default value on exception
                                  )(key))
                    for key in value)

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
            try:
                yaml_obj = yaml_round_trip_load(fh)
            except ScannerError as err:
                mark = err.problem_mark
                raise ConfigurationLoadError(
                    filepath,
                    "  reason: invalid yaml at line %(line)s, column %(column)s",
                    line=mark.line,
                    column=mark.column
                )
            except ReaderError as err:
                raise ConfigurationLoadError(filepath,
                                             "  reason: invalid yaml at position %(position)s",
                                             position=err.position)
            return cls.make_raw_parameters(filepath, yaml_obj) or EMPTY_MAP


class DefaultValueRawParameter(RawParameter):
    """
    Wraps a default value as a RawParameter, for usage in ParameterLoader.
    """

    def __init__(self, source, key, raw_value):
        super(DefaultValueRawParameter, self).__init__(source, key, raw_value)

        if isinstance(self._raw_value, Mapping):
            children_values = {}
            for k, v in self._raw_value.items():
                children_values[k] = DefaultValueRawParameter(self.source, self.key, v)
            self._value = frozendict(children_values)
        elif isiterable(self._raw_value):
            children_values = []
            for i in range(len(self._raw_value)):
                children_values.append(DefaultValueRawParameter(
                    self.source, self.key, self._raw_value[i]))
            self._value = tuple(children_values)
        elif isinstance(self._raw_value, ConfigurationObject):
            self._value = self._raw_value
            for attr_name, attr_value in vars(self._raw_value).items():
                self._value.__setattr__(
                    attr_name,
                    DefaultValueRawParameter(self.source, self.key, attr_value))
        elif isinstance(self._raw_value, Enum):
            self._value = self._raw_value
        elif isinstance(self._raw_value, primitive_types):
            self._value = self._raw_value
        else:
            raise ThisShouldNeverHappenError()  # pragma: no cover

    def value(self, parameter_obj):
        return self._value

    def keyflag(self):
        return None

    def valueflags(self, parameter_obj):
        if isinstance(self._raw_value, Mapping):
            return frozendict()
        elif isiterable(self._raw_value):
            return tuple()
        elif isinstance(self._raw_value, ConfigurationObject):
            return None
        elif isinstance(self._raw_value, Enum):
            return None
        elif isinstance(self._raw_value, primitive_types):
            return None
        else:
            raise ThisShouldNeverHappenError()  # pragma: no cover


def load_file_configs(search_path):
    # returns an ordered map of filepath and dict of raw parameter objects

    def _file_loader(fullpath):
        assert fullpath.endswith((".yml", ".yaml")) or "condarc" in basename(fullpath), fullpath
        yield fullpath, YamlRawParameter.make_raw_parameters_from_file(fullpath)

    def _dir_loader(fullpath):
        for filepath in sorted(
            p for p in (entry.path for entry in scandir(fullpath))
            if p[-4:] == ".yml" or p[-5:] == ".yaml"
        ):
            yield filepath, YamlRawParameter.make_raw_parameters_from_file(filepath)

    # map a stat result to a file loader or a directory loader
    _loader = {
        S_IFREG: _file_loader,
        S_IFDIR: _dir_loader,
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


class LoadedParameter(metaclass=ABCMeta):
    # (type) describes the type of parameter
    _type = None
    # (Parameter or type) if the LoadedParameter holds a collection, describes the element held in
    # the collection. if not, describes the primitive type held by the LoadedParameter.
    _element_type = None

    def __init__(self, name, value, key_flag, value_flags, validation=None):
        """
        Represents a Parameter that has been loaded with configuration value.

        Args:
            name (str): name of the loaded parameter
            value (LoadedParameter or primitive): the value of the loaded parameter
            key_flag (ParameterFlag or None): priority flag for the parameter itself
            value_flags (Any or None): priority flags for the parameter values
            validation (callable): Given a parameter value as input, return a boolean indicating
                validity, or alternately return a string describing an invalid value.
        """
        self._name = name
        self.value = value
        self.key_flag = key_flag
        self.value_flags = value_flags
        self._validation = validation

    def __eq__(self, other):
        if type(other) is type(self):
            return self.value == other.value
        return False

    def __hash__(self):
        return hash(self.value)

    def collect_errors(self, instance, typed_value, source="<<merged>>"):
        """
        Validate a LoadedParameter typed value.

        Args:
            instance (Configuration): the instance object used to create the LoadedParameter.
            typed_value (Any): typed value to validate.
            source (str): string description for the source of the typed_value.
        """
        errors = []
        if not isinstance(typed_value, self._type):
            errors.append(InvalidTypeError(self._name, typed_value, source, type(self.value),
                                           self._type))
        elif self._validation is not None:
            result = self._validation(typed_value)
            if result is False:
                errors.append(ValidationError(self._name, typed_value, source))
            elif isinstance(result, string_types):
                errors.append(CustomValidationError(self._name, typed_value, source, result))
        return errors

    def expand(self):
        """
        Recursively expands any environment values in the Loaded Parameter.

        Returns: LoadedParameter
        """
        # This is similar to conda.auxlib.type_coercion.typify_data_structure
        # It could be DRY-er but that would break SRP.
        if isinstance(self.value, Mapping):
            new_value = type(self.value)((k, v.expand()) for k, v in iteritems(self.value))
        elif isiterable(self.value):
            new_value = type(self.value)(v.expand() for v in self.value)
        elif isinstance(self.value, ConfigurationObject):
            for attr_name, attr_value in vars(self.value).items():
                if isinstance(attr_value, LoadedParameter):
                    self.value.__setattr__(attr_name, attr_value.expand())
            return self.value
        else:
            new_value = expand_environment_variables(self.value)
        self.value = new_value
        return self

    @abstractmethod
    def merge(self, matches):
        """
        Recursively merges matches into one LoadedParameter.

        Args:
            matches (List<LoadedParameter>): list of matches of this parameter.

        Returns: LoadedParameter
        """
        raise NotImplementedError()

    def typify(self, source):
        """
        Recursively types a LoadedParameter.

        Args:
            source (str): string describing the source of the LoadedParameter.

        Returns: a primitive, sequence, or map representing the typed value.
        """
        element_type = self._element_type
        try:
            return LoadedParameter._typify_data_structure(self.value, source, element_type)
        except TypeCoercionError as e:
            # if name is None:
            #     name = self.name
            msg = text_type(e)
            if issubclass(element_type, Enum):
                choices = ", ".join(map("'{}'".format, element_type.__members__.values()))
                msg += "\nValid choices for {}: {}".format(self._name, choices)
            raise CustomValidationError(self._name, e.value, source, msg)

    @staticmethod
    def _typify_data_structure(value, source, type_hint=None):
        if isinstance(value, Mapping):
            return type(value)((k, v.typify(source)) for k, v in iteritems(value))
        elif isiterable(value):
            return type(value)(v.typify(source) for v in value)
        elif isinstance(value, ConfigurationObject):
            for attr_name, attr_value in vars(value).items():
                if isinstance(attr_value, LoadedParameter):
                    value.__setattr__(attr_name, attr_value.typify(source))
            return value
        elif (isinstance(value, string_types)
              and isinstance(type_hint, type) and issubclass(type_hint, string_types)):
            # This block is necessary because if we fall through to typify(), we end up calling
            # .strip() on the str, when sometimes we want to preserve preceding and trailing
            # whitespace.
            return type_hint(value)
        else:
            return typify(value, type_hint)

    @staticmethod
    def _match_key_is_important(loaded_parameter):
        return loaded_parameter.key_flag is ParameterFlag.final

    @staticmethod
    def _first_important_matches(matches):
        idx = first(enumerate(matches),
                    lambda x: LoadedParameter._match_key_is_important(x[1]),
                    apply=lambda x: x[0])
        return matches if idx is None else matches[:idx+1]


class PrimitiveLoadedParameter(LoadedParameter):
    """
    LoadedParameter type that holds a single python primitive value.

    The python primitive types are str, int, float, complex, bool, and NoneType. In addition,
    python 2 has long and unicode types.
    """

    def __init__(self, name, element_type, value, key_flag, value_flags, validation=None):
        """
        Args:
            element_type (type or Tuple[type]): Type-validation of parameter's value.
            value (primitive value): primitive python value.
        """
        self._type = element_type
        self._element_type = element_type
        super(PrimitiveLoadedParameter, self).__init__(
            name, value, key_flag, value_flags, validation)

    def __eq__(self, other):
        if type(other) is type(self):
            return self.value == other.value
        return False

    def __hash__(self):
        return hash(self.value)

    def merge(self, matches):
        important_match = first(matches, LoadedParameter._match_key_is_important, default=None)
        if important_match is not None:
            return important_match

        last_match = last(matches, lambda x: x is not None, default=None)
        if last_match is not None:
            return last_match
        raise ThisShouldNeverHappenError()  # pragma: no cover


class MapLoadedParameter(LoadedParameter):
    """
    LoadedParameter type that holds a map (i.e. dict) of LoadedParameters.
    """
    _type = frozendict

    def __init__(self, name, value, element_type, key_flag, value_flags, validation=None):
        """
        Args:
            value (Mapping): Map of string keys to LoadedParameter values.
            element_type (Parameter): The Parameter type that is held in value.
            value_flags (Mapping): Map of priority value flags.
        """
        self._element_type = element_type
        super(MapLoadedParameter, self).__init__(name, value, key_flag, value_flags, validation)

    def collect_errors(self, instance, typed_value, source="<<merged>>"):
        errors = super(MapLoadedParameter, self).collect_errors(instance, typed_value, self.value)

        # recursively validate the values in the map
        if isinstance(self.value, Mapping):
            for key, value in iteritems(self.value):
                errors.extend(value.collect_errors(instance, typed_value[key], source))
        return errors

    def merge(self, matches):

        # get matches up to and including first important_match
        # but if no important_match, then all matches are important_matches
        relevant_matches_and_values = tuple((match, match.value) for match in
                                            LoadedParameter._first_important_matches(matches))

        for match, value in relevant_matches_and_values:
            if not isinstance(value, Mapping):
                raise InvalidTypeError(self.name, value, match.source, value.__class__.__name__,
                                       self._type.__name__)

        # map keys with important values
        def key_is_important(match, key):
            return match.value_flags.get(key) == ParameterFlag.final
        important_maps = tuple(dict((k, v)
                                    for k, v in iteritems(match_value)
                                    if key_is_important(match, k))
                               for match, match_value in relevant_matches_and_values)

        # map each value by recursively calling merge on any entries with the same key
        merged_values = frozendict(merge_with(
            lambda value_matches: value_matches[0].merge(value_matches),
            (match_value for _, match_value in relevant_matches_and_values)))

        # dump all matches in a dict
        # then overwrite with important matches
        merged_values_important_overwritten = frozendict(merge(
            concatv([merged_values], reversed(important_maps))))

        # create new parameter for the merged values
        return MapLoadedParameter(
            self._name,
            merged_values_important_overwritten,
            self._element_type,
            self.key_flag,
            self.value_flags,
            validation=self._validation)


class SequenceLoadedParameter(LoadedParameter):
    """
    LoadedParameter type that holds a sequence (i.e. list) of LoadedParameters.
    """
    _type = tuple

    def __init__(self, name, value, element_type, key_flag, value_flags, validation=None):
        """
        Args:
            value (Sequence): Sequence of LoadedParameter values.
            element_type (Parameter): The Parameter type that is held in the sequence.
            value_flags (Sequence): Sequence of priority value_flags.
        """
        self._element_type = element_type
        super(SequenceLoadedParameter, self).__init__(
            name, value, key_flag, value_flags, validation)

    def collect_errors(self, instance, typed_value, source="<<merged>>"):
        errors = super(SequenceLoadedParameter, self).collect_errors(
            instance, typed_value, self.value)
        # recursively collect errors on the elements in the sequence
        for idx, element in enumerate(self.value):
            errors.extend(element.collect_errors(instance, typed_value[idx], source))
        return errors

    def merge(self, matches):

        # get matches up to and including first important_match
        # but if no important_match, then all matches are important_matches
        relevant_matches_and_values = tuple((match, match.value) for match in
                                            LoadedParameter._first_important_matches(matches))
        for match, value in relevant_matches_and_values:
            if not isinstance(value, tuple):
                raise InvalidTypeError(self.name, value, match.source, value.__class__.__name__,
                                       self._type.__name__)

        # get individual lines from important_matches that were marked important
        # these will be prepended to the final result
        def get_marked_lines(match, marker):
            return tuple(line
                         for line, flag in zip(match.value,
                                               match.value_flags)
                         if flag is marker) if match else ()
        top_lines = concat(get_marked_lines(m, ParameterFlag.top) for m, _ in
                           relevant_matches_and_values)

        # also get lines that were marked as bottom, but reverse the match order so that lines
        # coming earlier will ultimately be last
        bottom_lines = concat(get_marked_lines(m, ParameterFlag.bottom) for m, _ in
                              reversed(relevant_matches_and_values))

        # now, concat all lines, while reversing the matches
        #   reverse because elements closer to the end of search path take precedence
        all_lines = concat(v for _, v in reversed(relevant_matches_and_values))

        # stack top_lines + all_lines, then de-dupe
        top_deduped = tuple(unique(concatv(top_lines, all_lines)))

        # take the top-deduped lines, reverse them, and concat with reversed bottom_lines
        # this gives us the reverse of the order we want, but almost there
        # NOTE: for a line value marked both top and bottom, the bottom marker will win out
        #       for the top marker to win out, we'd need one additional de-dupe step
        bottom_deduped = unique(concatv(reversed(tuple(bottom_lines)), reversed(top_deduped)))
        # just reverse, and we're good to go
        merged_values = tuple(reversed(tuple(bottom_deduped)))

        return SequenceLoadedParameter(
            self._name,
            merged_values,
            self._element_type,
            self.key_flag,
            self.value_flags,
            validation=self._validation)


class ObjectLoadedParameter(LoadedParameter):
    """
    LoadedParameter type that holds a sequence (i.e. list) of LoadedParameters.
    """
    _type = object

    def __init__(self, name, value, element_type, key_flag, value_flags, validation=None):
        """
        Args:
            value (Sequence): Object with LoadedParameter fields.
            element_type (object): The Parameter type that is held in the sequence.
            value_flags (Sequence): Sequence of priority value_flags.
        """
        self._element_type = element_type
        super(ObjectLoadedParameter, self).__init__(
            name, value, key_flag, value_flags, validation)

    def collect_errors(self, instance, typed_value, source="<<merged>>"):
        errors = super(ObjectLoadedParameter, self).collect_errors(
            instance, typed_value, self.value)

        # recursively validate the values in the object fields
        if isinstance(self.value, ConfigurationObject):
            for key, value in vars(self.value).items():
                if isinstance(value, LoadedParameter):
                    errors.extend(value.collect_errors(instance, typed_value[key], source))
        return errors

    def merge(self, matches):
        # get matches up to and including first important_match
        # but if no important_match, then all matches are important_matches
        relevant_matches_and_values = tuple((match,
                                             {k: v for k, v
                                              in vars(match.value).items()
                                              if isinstance(v, LoadedParameter)})
                                            for match
                                            in LoadedParameter._first_important_matches(matches))

        for match, value in relevant_matches_and_values:
            if not isinstance(value, Mapping):
                raise InvalidTypeError(self.name, value, match.source, value.__class__.__name__,
                                       self._type.__name__)

        # map keys with important values
        def key_is_important(match, key):
            return match.value_flags.get(key) == ParameterFlag.final
        important_maps = tuple(dict((k, v)
                                    for k, v in iteritems(match_value)
                                    if key_is_important(match, k))
                               for match, match_value in relevant_matches_and_values)

        # map each value by recursively calling merge on any entries with the same key
        merged_values = frozendict(merge_with(
            lambda value_matches: value_matches[0].merge(value_matches),
            (match_value for _, match_value in relevant_matches_and_values)))

        # dump all matches in a dict
        # then overwrite with important matches
        merged_values_important_overwritten = frozendict(merge(
            concatv([merged_values], reversed(important_maps))))

        # copy object and replace Parameter with LoadedParameter fields
        object_copy = copy.deepcopy(self._element_type)
        for attr_name, loaded_child_parameter in merged_values_important_overwritten.items():
            object_copy.__setattr__(attr_name, loaded_child_parameter)

        # create new parameter for the merged values
        return ObjectLoadedParameter(
            self._name,
            object_copy,
            self._element_type,
            self.key_flag,
            self.value_flags,
            validation=self._validation)


class ConfigurationObject(object):
    """
    Dummy class to mark whether a Python object has config parameters within.
    """
    pass


class Parameter(metaclass=ABCMeta):
    # (type) describes the type of parameter
    _type = None
    # (Parameter or type) if the Parameter is holds a collection, describes the element held in
    # the collection. if not, describes the primitive type held by the Parameter.
    _element_type = None

    def __init__(self, default, validation=None):
        """
        The Parameter class represents an unloaded configuration parameter, holding type, default
        and validation information until the parameter is loaded with a configuration.

        Args:
            default (Any): the typed, python representation default value given if the Parameter
                is not found in a Configuration.
            validation (callable): Given a parameter value as input, return a boolean indicating
                validity, or alternately return a string describing an invalid value.
        """
        self._default = default
        self._validation = validation

    @property
    def default(self):
        """
        Returns a DefaultValueRawParameter that wraps the actual default value.
        """
        wrapped_default = DefaultValueRawParameter("default", "default", self._default)
        return self.load("default", wrapped_default)

    def get_all_matches(self, name, names, instance):
        """
        Finds all matches of a Parameter in a Configuration instance

        Args:
            name (str): canonical name of the parameter to search for
            names (tuple(str)): alternative aliases of the parameter
            instance (Configuration): instance of the configuration to search within

        Returns (List(RawParameter)): matches of the parameter found in the configuration.
        """
        matches = []
        multikey_exceptions = []
        for filepath, raw_parameters in iteritems(instance.raw_data):
            match, error = ParameterLoader.raw_parameters_from_single_source(
                name, names, raw_parameters)
            if match is not None:
                matches.append(match)
            if error:
                multikey_exceptions.append(error)
        return matches, multikey_exceptions

    @abstractmethod
    def load(self, name, match):
        """
        Loads a Parameter with the value in a RawParameter.

        Args:
            name (str): name of the parameter to pass through
            match (RawParameter): the value of the RawParameter match

        Returns a LoadedParameter
        """
        raise NotImplementedError()

    def typify(self, name, source, value):
        element_type = self._element_type
        try:
            return typify_data_structure(value, element_type)
        except TypeCoercionError as e:
            # if name is None:
            #     name = self.name
            msg = text_type(e)
            if issubclass(element_type, Enum):
                choices = ", ".join(map("'{}'".format, element_type.__members__.values()))
                msg += "\nValid choices for {}: {}".format(name, choices)
            raise CustomValidationError(name, e.value, source, msg)


class PrimitiveParameter(Parameter):
    """
    Parameter type for a Configuration class that holds a single python primitive value.

    The python primitive types are str, int, float, complex, bool, and NoneType. In addition,
    python 2 has long and unicode types.
    """

    def __init__(self, default, element_type=None, validation=None):
        """
        Args:
            default (primitive value): default value if the Parameter is not found.
            element_type (type or Tuple[type]): Type-validation of parameter's value. If None,
                type(default) is used.
        """
        self._type = type(default) if element_type is None else element_type
        self._element_type = self._type
        super(PrimitiveParameter, self).__init__(default, validation)

    def load(self, name, match):
        return PrimitiveLoadedParameter(
            name,
            self._type,
            match.value(self._element_type),
            match.keyflag(),
            match.valueflags(self._element_type),
            validation=self._validation)


class MapParameter(Parameter):
    """
    Parameter type for a Configuration class that holds a map (i.e. dict) of Parameters.
    """
    _type = frozendict

    def __init__(self, element_type, default=frozendict(), validation=None):
        """
        Args:
            element_type (Parameter): The Parameter type held in the MapParameter.
            default (Mapping):  The parameter's default value. If None, will be an empty dict.
        """
        self._element_type = element_type
        default = default and frozendict(default) or frozendict()
        super(MapParameter, self).__init__(default, validation=validation)

    def get_all_matches(self, name, names, instance):
        # it also config settings like `proxy_servers: ~`
        matches, exceptions = super(MapParameter, self).get_all_matches(name, names, instance)
        matches = tuple(m for m in matches if m._raw_value is not None)
        return matches, exceptions

    def load(self, name, match):

        value = match.value(self._element_type)
        if value is None:
            return MapLoadedParameter(
                name,
                frozendict(),
                self._element_type,
                match.keyflag(),
                frozendict(),
                validation=self._validation)

        if not isinstance(value, Mapping):
            raise InvalidTypeError(name, value, match.source, value.__class__.__name__,
                                   self._type.__name__)

        loaded_map = {}
        for key, child_value in match.value(self._element_type).items():
            loaded_child_value = self._element_type.load(name, child_value)
            loaded_map[key] = loaded_child_value

        return MapLoadedParameter(
            name,
            frozendict(loaded_map),
            self._element_type,
            match.keyflag(),
            match.valueflags(self._element_type),
            validation=self._validation)


class SequenceParameter(Parameter):
    """
    Parameter type for a Configuration class that holds a sequence (i.e. list) of Parameters.
    """
    _type = tuple

    def __init__(self, element_type, default=(), validation=None, string_delimiter=','):
        """
        Args:
            element_type (Parameter): The Parameter type that is held in the sequence.
            default (Sequence): default value, empty tuple if not given.
            string_delimiter (str): separation string used to parse string into sequence.
        """
        self._element_type = element_type
        self.string_delimiter = string_delimiter
        super(SequenceParameter, self).__init__(default, validation)

    def get_all_matches(self, name, names, instance):
        # this is necessary to handle argparse `action="append"`, which can't be set to a
        #   default value of NULL
        # it also config settings like `channels: ~`
        matches, exceptions = super(SequenceParameter, self).get_all_matches(name, names, instance)
        matches = tuple(m for m in matches if m._raw_value is not None)
        return matches, exceptions

    def load(self, name, match):

        value = match.value(self)
        if value is None:
            return SequenceLoadedParameter(
                name,
                tuple(),
                self._element_type,
                match.keyflag(),
                tuple(),
                validation=self._validation)

        if not isiterable(value):
            raise InvalidTypeError(name, value, match.source, value.__class__.__name__,
                                   self._type.__name__)

        loaded_sequence = []
        for child_value in value:
            loaded_child_value = self._element_type.load(name, child_value)
            loaded_sequence.append(loaded_child_value)

        return SequenceLoadedParameter(
            name,
            tuple(loaded_sequence),
            self._element_type,
            match.keyflag(),
            match.valueflags(self._element_type),
            validation=self._validation)


class ObjectParameter(Parameter):
    """
    Parameter type for a Configuration class that holds an object with Parameter fields.
    """
    _type = object

    def __init__(self, element_type, default=ConfigurationObject(), validation=None):
        """
        Args:
            element_type (object): The object type with parameter fields held in ObjectParameter.
            default (Sequence): default value, empty tuple if not given.
        """
        self._element_type = element_type
        super(ObjectParameter, self).__init__(default, validation)

    def get_all_matches(self, name, names, instance):
        # it also config settings like `proxy_servers: ~`
        matches, exceptions = super(ObjectParameter, self).get_all_matches(name, names, instance)
        matches = tuple(m for m in matches if m._raw_value is not None)
        return matches, exceptions

    def load(self, name, match):

        value = match.value(self._element_type)
        if value is None:
            return ObjectLoadedParameter(
                name,
                None,
                self._element_type,
                match.keyflag(),
                None,
                validation=self._validation)

        if not (isinstance(value, Mapping) or isinstance(value, ConfigurationObject)):
            raise InvalidTypeError(name, value, match.source, value.__class__.__name__,
                                   self._type.__name__)

        # for a default object, extract out the instance variables
        if isinstance(value, ConfigurationObject):
            value = vars(value)

        object_parameter_attrs = {attr_name: parameter_type
                                  for attr_name, parameter_type
                                  in vars(self._element_type).items()
                                  if isinstance(parameter_type, Parameter)
                                  and attr_name in value.keys()}

        # recursively load object fields
        loaded_attrs = {}
        for attr_name, parameter_type in object_parameter_attrs.items():
            raw_child_value = value.get(attr_name)
            loaded_child_value = parameter_type.load(name, raw_child_value)
            loaded_attrs[attr_name] = loaded_child_value

        # copy object and replace Parameter with LoadedParameter fields
        object_copy = copy.deepcopy(self._element_type)
        for attr_name, loaded_child_parameter in loaded_attrs.items():
            object_copy.__setattr__(attr_name, loaded_child_parameter)

        return ObjectLoadedParameter(
            name,
            object_copy,
            self._element_type,
            match.keyflag(),
            match.valueflags(self._element_type),
            validation=self._validation)


class ParameterLoader(object):
    """
    ParameterLoader class contains the top level logic needed to load a parameter from start to
    finish.
    """

    def __init__(self, parameter_type, aliases=(), expandvars=False):
        """
        Args:
            parameter_type (Parameter): the type of Parameter that is stored in the loader.
            aliases (tuple(str)): alternative aliases for the Parameter
            expandvars (bool): whether or not to recursively expand environmental variables.
        """
        self._name = None
        self._names = None
        self.type = parameter_type
        self.aliases = aliases
        self._expandvars = expandvars

    def _set_name(self, name):
        # this is an explicit method, and not a descriptor/setter
        # it's meant to be called by the Configuration metaclass
        self._name = name  # lgtm [py/mutable-descriptor]
        _names = frozenset(x for x in chain(self.aliases, (name, )))
        self._names = _names  # lgtm [py/mutable-descriptor]
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

    def __get__(self, instance, instance_type):
        # strategy is "extract and merge," which is actually just map and reduce
        # extract matches from each source in SEARCH_PATH
        # then merge matches together
        if self.name in instance._cache_:
            return instance._cache_[self.name]

        # step 1/2: load config and find top level matches
        raw_matches, errors = self.type.get_all_matches(self.name, self.names, instance)

        # step 3: parse RawParameters into LoadedParameters
        matches = [self.type.load(self.name, match) for match in raw_matches]

        # step 4: merge matches
        merged = matches[0].merge(matches) if matches else self.type.default

        # step 5: typify
        # We need to expand any environment variables before type casting.
        # Otherwise e.g. `my_bool_var: $BOOL` with BOOL=True would raise a TypeCoercionError.
        expanded = merged.expand() if self._expandvars else merged
        try:
            result = expanded.typify("<<merged>>")
        except CustomValidationError as e:
            errors.append(e)
        else:
            errors.extend(expanded.collect_errors(instance, result, "<<merged>>"))
        raise_errors(errors)
        instance._cache_[self.name] = result  # lgtm [py/uninitialized-local-variable]
        return result  # lgtm [py/uninitialized-local-variable]

    def _raw_parameters_from_single_source(self, raw_parameters):
        return ParameterLoader.raw_parameters_from_single_source(
            self.name, self.names, raw_parameters)

    @staticmethod
    def raw_parameters_from_single_source(name, names, raw_parameters):
        # while supporting parameter name aliases, we enforce that only one definition is given
        # per data source
        keys = names & frozenset(raw_parameters.keys())
        matches = {key: raw_parameters[key] for key in keys}
        numkeys = len(keys)
        if numkeys == 0:
            return None, None
        elif numkeys == 1:
            return next(itervalues(matches)), None
        elif name in keys:
            return matches[name], MultipleKeysError(
                raw_parameters[next(iter(keys))].source, keys, name)
        else:
            return None, MultipleKeysError(raw_parameters[next(iter(keys))].source,
                                           keys, name)


class ConfigurationType(type):
    """metaclass for Configuration"""

    def __init__(cls, name, bases, attr):
        super(ConfigurationType, cls).__init__(name, bases, attr)

        # call _set_name for each parameter
        cls.parameter_names = tuple(p._set_name(name) for name, p in iteritems(cls.__dict__)
                                    if isinstance(p, ParameterLoader))


class Configuration(metaclass=ConfigurationType):

    def __init__(self, search_path=(), app_name=None, argparse_args=None):
        # Currently, __init__ does a **full** disk reload of all files.
        # A future improvement would be to cache files that are already loaded.
        self.raw_data = odict()
        self._cache_ = dict()
        self._reset_callbacks = IndexedSet()
        self._validation_errors = defaultdict(list)

        self._set_search_path(search_path)
        self._set_env_vars(app_name)
        self._set_argparse_args(argparse_args)

    def _set_search_path(self, search_path):
        self._search_path = IndexedSet(search_path)
        self._set_raw_data(load_file_configs(search_path))
        self._reset_cache()
        return self

    def _set_env_vars(self, app_name=None):
        self._app_name = app_name
        if not app_name:
            return self
        self.raw_data[EnvRawParameter.source] = EnvRawParameter.make_raw_parameters(app_name)
        self._reset_cache()
        return self

    def _set_argparse_args(self, argparse_args):
        # the argparse_args we store internally in this class as self._argparse_args
        #   will be a mapping type, not a non-`dict` object like argparse_args is natively
        if hasattr(argparse_args, '__dict__'):
            # the argparse_args from argparse will be an object with a __dict__ attribute
            #   and not a mapping type like this method will turn it into
            self._argparse_args = AttrDict((k, v) for k, v, in iteritems(vars(argparse_args))
                                           if v is not NULL)
        elif not argparse_args:
            # argparse_args can be initialized as `None`
            self._argparse_args = AttrDict()
        else:
            # we're calling this method with argparse_args that are a mapping type, likely
            #   already having been processed by this method before
            self._argparse_args = AttrDict((k, v) for k, v, in iteritems(argparse_args)
                                           if v is not NULL)

        source = ArgParseRawParameter.source
        self.raw_data[source] = ArgParseRawParameter.make_raw_parameters(self._argparse_args)
        self._reset_cache()
        return self

    def _set_raw_data(self, raw_data):
        self.raw_data.update(raw_data)
        self._reset_cache()
        return self

    def _reset_cache(self):
        self._cache_ = dict()
        for callback in self._reset_callbacks:
            callback()
        return self

    def register_reset_callaback(self, callback):
        self._reset_callbacks.add(callback)

    def check_source(self, source):
        # this method ends up duplicating much of the logic of Parameter.__get__
        # I haven't yet found a way to make it more DRY though
        typed_values = {}
        validation_errors = []
        raw_parameters = self.raw_data[source]
        for key in self.parameter_names:
            parameter = self.__class__.__dict__[key]
            match, multikey_error = parameter._raw_parameters_from_single_source(raw_parameters)
            if multikey_error:
                validation_errors.append(multikey_error)

            if match is not None:
                loaded_parameter = parameter.type.load(key, match)
                # untyped_value = loaded_parameter.value
                # if untyped_value is None:
                #     if isinstance(parameter, SequenceLoadedParameter):
                #         untyped_value = ()
                #     elif isinstance(parameter, MapLoadedParameter):
                #         untyped_value = {}
                try:
                    typed_value = loaded_parameter.typify(match.source)
                except CustomValidationError as e:
                    validation_errors.append(e)
                else:
                    collected_errors = loaded_parameter.collect_errors(
                        self, typed_value, match.source)
                    if collected_errors:
                        validation_errors.extend(collected_errors)
                    else:
                        typed_values[match.key] = typed_value
            else:
                # this situation will happen if there is a multikey_error and none of the
                # matched keys is the primary key
                pass
        return typed_values, validation_errors

    def validate_all(self):
        validation_errors = list(chain.from_iterable(self.check_source(source)[1]
                                                     for source in self.raw_data))
        raise_errors(validation_errors)
        self.validate_configuration()

    @staticmethod
    def _collect_validation_error(func, *args, **kwargs):
        try:
            func(*args, **kwargs)
        except ConfigurationError as e:
            return e.errors if hasattr(e, 'errors') else e,
        return ()

    def validate_configuration(self):
        errors = chain.from_iterable(Configuration._collect_validation_error(getattr, self, name)
                                     for name in self.parameter_names)
        post_errors = self.post_build_validation()
        raise_errors(tuple(chain.from_iterable((errors, post_errors))))

    def post_build_validation(self):
        return ()

    def collect_all(self):
        typed_values = odict()
        validation_errors = odict()
        for source in self.raw_data:
            typed_values[source], validation_errors[source] = self.check_source(source)
        raise_errors(tuple(chain.from_iterable(itervalues(validation_errors))))
        return odict((k, v) for k, v in iteritems(typed_values) if v)

    def describe_parameter(self, parameter_name):
        # TODO, in Parameter base class, rename element_type to value_type
        if parameter_name not in self.parameter_names:
            parameter_name = '_' + parameter_name
        parameter_loader = self.__class__.__dict__[parameter_name]
        parameter = parameter_loader.type
        assert isinstance(parameter, Parameter)

        # dedupe leading underscore from name
        name = parameter_loader.name.lstrip('_')
        aliases = tuple(alias for alias in parameter_loader.aliases if alias != name)

        description = self.get_descriptions().get(name, '')
        et = parameter._element_type
        if type(et) == EnumMeta:
            et = [et]
        if not isiterable(et):
            et = [et]

        if isinstance(parameter._element_type, Parameter):
            element_types = tuple(
                _et.__class__.__name__.lower().replace("parameter", "") for _et in et)
        else:
            element_types = tuple(_et.__name__ for _et in et)

        details = {
            'parameter_type': parameter.__class__.__name__.lower().replace("parameter", ""),
            'name': name,
            'aliases': aliases,
            'element_types': element_types,
            'default_value': parameter.default.typify("<<describe>>"),
            'description': description.replace('\n', ' ').strip(),
        }
        if isinstance(parameter, SequenceParameter):
            details['string_delimiter'] = parameter.string_delimiter
        return details

    def list_parameters(self):
        return tuple(sorted(name.lstrip('_') for name in self.parameter_names))

    def typify_parameter(self, parameter_name, value, source):
        # return a tuple with correct parameter name and typed-value
        if parameter_name not in self.parameter_names:
            parameter_name = '_' + parameter_name
        parameter_loader = self.__class__.__dict__[parameter_name]
        parameter = parameter_loader.type
        assert isinstance(parameter, Parameter)

        return parameter.typify(parameter_name, source, value)

    def get_descriptions(self):
        raise NotImplementedError()
