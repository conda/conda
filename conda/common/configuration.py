# -*- coding: utf-8 -*-
"""
A generalized application configuration utility.

Features include:
  - lazy eval
  - merges configuration files
  - parameter type validation, with custom validation
  - parameter aliases

Easily extensible to other source formats, e.g. json and ini

Limitations:
  - at the moment only supports a "flat" config structure; no nested data structures

"""
from __future__ import absolute_import, division, print_function, unicode_literals

from abc import ABCMeta, abstractmethod
from collections import Mapping, defaultdict
from glob import glob
from itertools import chain
from logging import getLogger
from os import environ, stat
from os.path import basename, join
from stat import S_IFDIR, S_IFMT, S_IFREG

from enum import Enum

from .compat import (isiterable, iteritems, itervalues, odict, primitive_types, string_types,
                     text_type, with_metaclass)
from .constants import EMPTY_MAP, NULL
from .yaml import yaml_load
from .. import CondaError, CondaMultiError
from .._vendor.auxlib.collection import AttrDict, first, frozendict, last, make_immutable
from .._vendor.auxlib.exceptions import ThisShouldNeverHappenError
from .._vendor.auxlib.path import expand
from .._vendor.auxlib.type_coercion import TypeCoercionError, typify_data_structure

try:
    from cytoolz.dicttoolz import merge
    from cytoolz.functoolz import excepts
    from cytoolz.itertoolz import concat, concatv, unique
except ImportError:
    from .._vendor.toolz.dicttoolz import merge
    from .._vendor.toolz.functoolz import excepts
    from .._vendor.toolz.itertoolz import concat, concatv, unique
try:
    from ruamel_yaml.comments import CommentedSeq, CommentedMap
    from ruamel_yaml.scanner import ScannerError
except ImportError:  # pragma: no cover
    from ruamel.yaml.comments import CommentedSeq, CommentedMap  # pragma: no cover
    from ruamel.yaml.scanner import ScannerError

log = getLogger(__name__)


def pretty_list(iterable, padding='  '):  # TODO: move elsewhere in conda.common
    if not isiterable(iterable):
        iterable = [iterable]
    return '\n'.join("%s- %s" % (padding, item) for item in iterable)


def pretty_map(dictionary, padding='  '):
    return '\n'.join("%s%s: %s" % (padding, key, value) for key, value in iteritems(dictionary))


class LoadError(CondaError):
    def __init__(self, message, filepath, line, column):
        self.line = line
        self.filepath = filepath
        self.column = column
        msg = "Load Error: in %s on line %s, column %s. %s" % (filepath, line, column, message)
        super(LoadError, self).__init__(msg)


class ConfigurationError(CondaError):
    pass


class ValidationError(ConfigurationError):

    def __init__(self, parameter_name, parameter_value, source, msg=None, **kwargs):
        self.parameter_name = parameter_name
        self.parameter_value = parameter_value
        self.source = source
        super(ConfigurationError, self).__init__(msg, **kwargs)


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
                   "Valid types: %s." % (parameter_name, parameter_value,
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
    final = 'final'
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


@with_metaclass(ABCMeta)
class RawParameter(object):

    def __init__(self, source, key, raw_value):
        self.source = source
        self.key = key
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
        if hasattr(parameter_obj, 'string_delimiter'):
            string_delimiter = getattr(parameter_obj, 'string_delimiter')
            # TODO: add stripping of !important, !top, and !bottom
            raw_value = self._raw_value
            if string_delimiter in raw_value:
                value = raw_value.split(string_delimiter)
            else:
                value = [raw_value]
            return tuple(v.strip() for v in value)
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
        return make_immutable(self._raw_value)

    def keyflag(self):
        return None

    def valueflags(self, parameter_obj):
        return None if isinstance(parameter_obj, PrimitiveParameter) else ()

    @classmethod
    def make_raw_parameters(cls, args_from_argparse):
        return super(ArgParseRawParameter, cls).make_raw_parameters(ArgParseRawParameter.source,
                                                                    args_from_argparse)


class YamlRawParameter(RawParameter):
    # this class should encapsulate all direct use of ruamel.yaml in this module

    def __init__(self, source, key, raw_value, keycomment):
        self._keycomment = keycomment
        super(YamlRawParameter, self).__init__(source, key, raw_value)

    def value(self, parameter_obj):
        self.__process(parameter_obj)
        return self._value

    def keyflag(self):
        return ParameterFlag.from_string(self._keycomment)

    def valueflags(self, parameter_obj):
        self.__process(parameter_obj)
        return self._valueflags

    def __process(self, parameter_obj):
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
        return dict((key, excepts(KeyError,
                                  lambda k: rawvalue.ca.items[k][2].value.strip() or None,
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
            try:
                ruamel_yaml = yaml_load(fh)
            except ScannerError as err:
                mark = err.problem_mark
                raise LoadError("Invalid YAML", filepath, mark.line, mark.column)
        return cls.make_raw_parameters(filepath, ruamel_yaml) or EMPTY_MAP


def load_file_configs(search_path):
    # returns an ordered map of filepath and dict of raw parameter objects

    def _file_yaml_loader(fullpath):
        assert fullpath.endswith((".yml", ".yaml")) or "condarc" in basename(fullpath), fullpath
        yield fullpath, YamlRawParameter.make_raw_parameters_from_file(fullpath)

    def _dir_yaml_loader(fullpath):
        for filepath in sorted(concatv(glob(join(fullpath, "*.yml")),
                                       glob(join(fullpath, "*.yaml")))):
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

    def _raw_parameters_from_single_source(self, raw_parameters):
        # while supporting parameter name aliases, we enforce that only one definition is given
        # per data source
        keys = self.names & frozenset(raw_parameters.keys())
        matches = {key: raw_parameters[key] for key in keys}
        numkeys = len(keys)
        if numkeys == 0:
            return None, None
        elif numkeys == 1:
            return next(itervalues(matches)), None
        elif self.name in keys:
            return matches[self.name], MultipleKeysError(raw_parameters[next(iter(keys))].source,
                                                         keys, self.name)
        else:
            return None, MultipleKeysError(raw_parameters[next(iter(keys))].source,
                                           keys, self.name)

    def _get_all_matches(self, instance):
        # a match is a raw parameter instance
        matches = []
        multikey_exceptions = []
        for filepath, raw_parameters in iteritems(instance.raw_data):
            match, error = self._raw_parameters_from_single_source(raw_parameters)
            if match is not None:
                matches.append(match)
            if error:
                multikey_exceptions.append(error)
        return matches, multikey_exceptions

    @abstractmethod
    def _merge(self, matches):
        raise NotImplementedError()

    def __get__(self, instance, instance_type):
        # strategy is "extract and merge," which is actually just map and reduce
        # extract matches from each source in SEARCH_PATH
        # then merge matches together
        if self.name in instance._cache_:
            return instance._cache_[self.name]

        matches, errors = self._get_all_matches(instance)
        try:
            result = typify_data_structure(self._merge(matches) if matches else self.default,
                                           self._element_type)
        except TypeCoercionError as e:
            errors.append(CustomValidationError(self.name, e.value, "<<merged>>", text_type(e)))
        else:
            errors.extend(self.collect_errors(instance, result))
        raise_errors(errors)
        instance._cache_[self.name] = result
        return result

    def collect_errors(self, instance, value, source="<<merged>>"):
        """Validate a Parameter value.

        Args:
            instance (Configuration): The instance object to which the Parameter descriptor is
                attached.
            value: The value to be validated.

        """
        errors = []
        if not isinstance(value, self._type):
            errors.append(InvalidTypeError(self.name, value, source, type(value),
                                           self._type))
        elif self._validation is not None:
            result = self._validation(value)
            if result is False:
                errors.append(ValidationError(self.name, value, source))
            elif isinstance(result, string_types):
                errors.append(CustomValidationError(self.name, value, source, result))
        return errors

    def _match_key_is_important(self, raw_parameter):
        return raw_parameter.keyflag() is ParameterFlag.final

    def _first_important_matches(self, matches):
        idx = first(enumerate(matches), lambda x: self._match_key_is_important(x[1]),
                    apply=lambda x: x[0])
        return matches if idx is None else matches[:idx+1]

    @staticmethod
    def _str_format_flag(flag):
        return "  #!%s" % flag if flag is not None else ''

    @staticmethod
    def _str_format_value(value):
        if value is None:
            return 'None'
        return value

    @classmethod
    def repr_raw(cls, raw_parameter):
        raise NotImplementedError()


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
                validity, or alternately return a string describing an invalid value. Returning
                `None` also indicates a valid value.
            parameter_type (type or Tuple[type]): Type-validation of parameter's value. If None,
                type(default) is used.

        """
        self._type = type(default) if parameter_type is None else parameter_type
        self._element_type = self._type
        super(PrimitiveParameter, self).__init__(default, aliases, validation)

    def _merge(self, matches):
        important_match = first(matches, self._match_key_is_important, default=None)
        if important_match is not None:
            return important_match.value(self)

        last_match = last(matches, lambda x: x is not None, default=None)
        if last_match is not None:
            return last_match.value(self)
        raise ThisShouldNeverHappenError()  # pragma: no cover

    def repr_raw(self, raw_parameter):
        return "%s: %s%s" % (raw_parameter.key,
                             self._str_format_value(raw_parameter.value(self)),
                             self._str_format_flag(raw_parameter.keyflag()))


class SequenceParameter(Parameter):
    """Parameter type for a Configuration class that holds a sequence (i.e. list) of python
    primitive values.
    """
    _type = tuple

    def __init__(self, element_type, default=(), aliases=(), validation=None,
                 string_delimiter=','):
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
        self.string_delimiter = string_delimiter
        super(SequenceParameter, self).__init__(default, aliases, validation)

    def collect_errors(self, instance, value, source="<<merged>>"):
        errors = super(SequenceParameter, self).collect_errors(instance, value)

        element_type = self._element_type
        for idx, element in enumerate(value):
            if not isinstance(element, element_type):
                errors.append(InvalidElementTypeError(self.name, element, source,
                                                      type(element), element_type, idx))
        return errors

    def _merge(self, matches):
        # get matches up to and including first important_match
        #   but if no important_match, then all matches are important_matches
        relevant_matches = self._first_important_matches(matches)

        # get individual lines from important_matches that were marked important
        # these will be prepended to the final result
        def get_marked_lines(match, marker, parameter_obj):
            return tuple(line
                         for line, flag in zip(match.value(parameter_obj),
                                               match.valueflags(parameter_obj))
                         if flag is marker) if match else ()
        top_lines = concat(get_marked_lines(m, ParameterFlag.top, self) for m in relevant_matches)

        # also get lines that were marked as bottom, but reverse the match order so that lines
        # coming earlier will ultimately be last
        bottom_lines = concat(get_marked_lines(m, ParameterFlag.bottom, self) for m in
                              reversed(relevant_matches))

        # now, concat all lines, while reversing the matches
        #   reverse because elements closer to the end of search path take precedence
        all_lines = concat(m.value(self) for m in reversed(relevant_matches))

        # stack top_lines + all_lines, then de-dupe
        top_deduped = tuple(unique(concatv(top_lines, all_lines)))

        # take the top-deduped lines, reverse them, and concat with reversed bottom_lines
        # this gives us the reverse of the order we want, but almost there
        # NOTE: for a line value marked both top and bottom, the bottom marker will win out
        #       for the top marker to win out, we'd need one additional de-dupe step
        bottom_deduped = unique(concatv(reversed(tuple(bottom_lines)), reversed(top_deduped)))
        # just reverse, and we're good to go
        return tuple(reversed(tuple(bottom_deduped)))

    def repr_raw(self, raw_parameter):
        lines = list()
        lines.append("%s:%s" % (raw_parameter.key,
                                self._str_format_flag(raw_parameter.keyflag())))
        for q, value in enumerate(raw_parameter.value(self)):
            valueflag = raw_parameter.valueflags(self)[q]
            lines.append("  - %s%s" % (self._str_format_value(value),
                                       self._str_format_flag(valueflag)))
        return '\n'.join(lines)

    def _get_all_matches(self, instance):
        # this is necessary to handle argparse `action="append"`, which can't be set to a
        #   default value of NULL
        matches, multikey_exceptions = super(SequenceParameter, self)._get_all_matches(instance)
        matches = tuple(m for m in matches if m._raw_value is not None)
        return matches, multikey_exceptions


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

    def collect_errors(self, instance, value, source="<<merged>>"):
        errors = super(MapParameter, self).collect_errors(instance, value)
        if isinstance(value, Mapping):
            element_type = self._element_type
            errors.extend(InvalidElementTypeError(self.name, val, source, type(val),
                                                  element_type, key)
                          for key, val in iteritems(value) if not isinstance(val, element_type))
        return errors

    def _merge(self, matches):
        # get matches up to and including first important_match
        #   but if no important_match, then all matches are important_matches
        relevant_matches = self._first_important_matches(matches)

        # mapkeys with important matches
        def key_is_important(match, key):
            return match.valueflags(self).get(key) is ParameterFlag.final
        important_maps = tuple(dict((k, v)
                                    for k, v in iteritems(match.value(self))
                                    if key_is_important(match, k))
                               for match in relevant_matches)
        # dump all matches in a dict
        # then overwrite with important matches
        return merge(concatv((m.value(self) for m in relevant_matches),
                             reversed(important_maps)))

    def repr_raw(self, raw_parameter):
        lines = list()
        lines.append("%s:%s" % (raw_parameter.key,
                                self._str_format_flag(raw_parameter.keyflag())))
        for valuekey, value in iteritems(raw_parameter.value(self)):
            valueflag = raw_parameter.valueflags(self).get(valuekey)
            lines.append("  %s: %s%s" % (valuekey, self._str_format_value(value),
                                         self._str_format_flag(valueflag)))
        return '\n'.join(lines)


class ConfigurationType(type):
    """metaclass for Configuration"""

    def __init__(cls, name, bases, attr):
        super(ConfigurationType, cls).__init__(name, bases, attr)

        # call _set_name for each parameter
        cls.parameter_names = tuple(p._set_name(name) for name, p in iteritems(cls.__dict__)
                                    if isinstance(p, Parameter))


@with_metaclass(ConfigurationType)
class Configuration(object):

    def __init__(self, search_path=(), app_name=None, argparse_args=None):
        self.raw_data = odict()
        self._cache_ = dict()
        self._reset_callbacks = set()  # TODO: make this a boltons ordered set
        self._validation_errors = defaultdict(list)

        if not hasattr(self, '_search_path') and search_path is not None:
            # we only set search_path once; we never change it
            self._search_path = search_path

        if not hasattr(self, '_app_name') and app_name is not None:
            # we only set app_name once; we never change it
            self._app_name = app_name

        self._set_search_path(search_path)
        self._set_env_vars(app_name)
        self._set_argparse_args(argparse_args)

    def _set_search_path(self, search_path):
        if not hasattr(self, '_search_path') and search_path is not None:
            # we only set search_path once; we never change it
            self._search_path = search_path

        if getattr(self, '_search_path', None):

            # we need to make sure old data doesn't stick around if we are resetting
            #   easiest solution is to completely clear raw_data and re-load other sources
            #   if raw_data holds contents
            raw_data_held_contents = bool(self.raw_data)
            if raw_data_held_contents:
                self.raw_data = odict()

            self._set_raw_data(load_file_configs(search_path))

            if raw_data_held_contents:
                # this should only be triggered on re-initialization / reset
                self._set_env_vars(getattr(self, '_app_name', None))
                self._set_argparse_args(self._argparse_args)

        self._reset_cache()
        return self

    def _set_env_vars(self, app_name=None):
        if not hasattr(self, '_app_name') and app_name is not None:
            # we only set app_name once; we never change it
            self._app_name = app_name
        if getattr(self, '_app_name', None):
            erp = EnvRawParameter
            self.raw_data[erp.source] = erp.make_raw_parameters(self._app_name)
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
                try:
                    typed_value = typify_data_structure(match.value(parameter),
                                                        parameter._element_type)
                except TypeCoercionError as e:
                    validation_errors.append(CustomValidationError(match.key, e.value,
                                                                   match.source, text_type(e)))
                else:
                    collected_errors = parameter.collect_errors(self, typed_value, match.source)
                    if collected_errors:
                        validation_errors.extend(collected_errors)
                    else:
                        typed_values[match.key] = typed_value  # parameter.repr_raw(match)
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
