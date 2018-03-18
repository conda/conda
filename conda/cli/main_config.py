# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
from __future__ import absolute_import, division, print_function, unicode_literals

import collections
import json
import os
from os.path import isfile, join
import sys
from textwrap import wrap

from .. import CondaError
from .._vendor.auxlib.entity import EntityEncoder
from ..base.constants import PathConflict, SafetyChecks
from ..base.context import context, sys_rc_path, user_rc_path
from ..common.compat import isiterable, iteritems, itervalues, string_types, text_type
from ..common.configuration import pretty_list, pretty_map
from ..common.io import timeout
from ..common.serialize import yaml, yaml_dump, yaml_load

try:
    from cytoolz.itertoolz import concat, groupby
except ImportError:  # pragma: no cover
    from .._vendor.toolz.itertoolz import concat, groupby  # NOQA


def execute(args, parser):
    from ..exceptions import CouldntParseError
    try:
        execute_config(args, parser)
    except (CouldntParseError, NotImplementedError) as e:
        raise CondaError(e)


def format_dict(d):
    lines = []
    for k, v in iteritems(d):
        if isinstance(v, collections.Mapping):
            if v:
                lines.append("%s:" % k)
                lines.append(pretty_map(v))
            else:
                lines.append("%s: {}" % k)
        elif isiterable(v):
            if v:
                lines.append("%s:" % k)
                lines.append(pretty_list(v))
            else:
                lines.append("%s: []" % k)
        else:
            lines.append("%s: %s" % (k, v if v is not None else "None"))
    return lines


def parameter_description_builder(name):
    builder = []
    details = context.describe_parameter(name)
    aliases = details['aliases']
    string_delimiter = details.get('string_delimiter')
    element_types = details['element_types']
    default_value_str = json.dumps(details['default_value'], cls=EntityEncoder)

    if details['parameter_type'] == 'primitive':
        builder.append("%s (%s)" % (name, ', '.join(sorted(set(et for et in element_types)))))
    else:
        builder.append("%s (%s: %s)" % (name, details['parameter_type'],
                                        ', '.join(sorted(set(et for et in element_types)))))

    if aliases:
        builder.append("  aliases: %s" % ', '.join(aliases))
    if string_delimiter:
        builder.append("  string delimiter: '%s'" % string_delimiter)

    builder.extend('  ' + line for line in wrap(details['description'], 70))

    builder.append('')

    builder.extend(yaml_dump({name: json.loads(default_value_str)}).strip().split('\n'))

    builder = ['# ' + line for line in builder]
    builder.append('')
    builder.append('')
    return builder


def execute_config(args, parser):

    json_warnings = []
    json_get = {}

    if args.show_sources:
        if context.json:
            print(json.dumps(context.collect_all(), sort_keys=True,
                             indent=2, separators=(',', ': ')))
        else:
            lines = []
            for source, reprs in iteritems(context.collect_all()):
                lines.append("==> %s <==" % source)
                lines.extend(format_dict(reprs))
                lines.append('')
            print('\n'.join(lines))
        return

    if args.show is not None:
        if args.show:
            paramater_names = args.show
            all_names = context.list_parameters()
            not_params = set(paramater_names) - set(all_names)
            if not_params:
                from ..exceptions import ArgumentError
                from ..resolve import dashlist
                raise ArgumentError("Invalid configuration parameters: %s" % dashlist(not_params))
        else:
            paramater_names = context.list_parameters()

        from collections import OrderedDict

        d = OrderedDict((key, getattr(context, key)) for key in paramater_names)
        if context.json:
            print(json.dumps(d, sort_keys=True, indent=2, separators=(',', ': '),
                  cls=EntityEncoder))
        else:
            # coerce channels
            if 'custom_channels' in d:
                d['custom_channels'] = {
                    channel.name: "%s://%s" % (channel.scheme, channel.location)
                    for channel in itervalues(d['custom_channels'])
                }
            # TODO: custom_multichannels needs better formatting
            if 'custom_multichannels' in d:
                d['custom_multichannels'] = {k: json.dumps([text_type(c) for c in chnls],
                                                           ensure_ascii=False)
                                             for k, chnls in iteritems(d['custom_multichannels'])}

            print('\n'.join(format_dict(d)))
        context.validate_configuration()
        return

    if args.describe is not None:
        if args.describe:
            paramater_names = args.describe
            all_names = context.list_parameters()
            not_params = set(paramater_names) - set(all_names)
            if not_params:
                from ..exceptions import ArgumentError
                from ..resolve import dashlist
                raise ArgumentError("Invalid configuration parameters: %s" % dashlist(not_params))
        else:
            paramater_names = context.list_parameters()
        if context.json:
            print(json.dumps([context.describe_parameter(name) for name in paramater_names],
                             sort_keys=True, indent=2, separators=(',', ': '),
                             cls=EntityEncoder))
        else:
            print('\n'.join(concat(parameter_description_builder(name)
                                   for name in paramater_names)))
        return

    if args.validate:
        context.validate_all()
        return

    if args.system:
        rc_path = sys_rc_path
    elif args.env:
        if 'CONDA_PREFIX' in os.environ:
            rc_path = join(os.environ['CONDA_PREFIX'], '.condarc')
        else:
            rc_path = user_rc_path
    elif args.file:
        rc_path = args.file
    else:
        rc_path = user_rc_path

    if args.write_default:
        if isfile(rc_path):
            with open(rc_path) as fh:
                data = fh.read().strip()
            if data:
                raise CondaError("The file '%s' "
                                 "already contains configuration information.\n"
                                 "Remove the file to proceed.\n"
                                 "Use `conda config --describe` to display default configuration."
                                 % rc_path)

        with open(rc_path, 'w') as fh:
            paramater_names = context.list_parameters()
            fh.write('\n'.join(concat(parameter_description_builder(name)
                                      for name in paramater_names)))
        return

    # read existing condarc
    if os.path.exists(rc_path):
        with open(rc_path, 'r') as fh:
            rc_config = yaml_load(fh) or {}
    else:
        rc_config = {}

    grouped_paramaters = groupby(lambda p: context.describe_parameter(p)['parameter_type'],
                                 context.list_parameters())
    primitive_parameters = grouped_paramaters['primitive']
    sequence_parameters = grouped_paramaters['sequence']
    map_parameters = grouped_paramaters['map']

    # Get
    if args.get is not None:
        context.validate_all()
        if args.get == []:
            args.get = sorted(rc_config.keys())
        for key in args.get:
            if key not in primitive_parameters + sequence_parameters:
                message = "unknown key %s" % key
                if not context.json:
                    print(message, file=sys.stderr)
                else:
                    json_warnings.append(message)
                continue
            if key not in rc_config:
                continue

            if context.json:
                json_get[key] = rc_config[key]
                continue

            if isinstance(rc_config[key], (bool, string_types)):
                print("--set", key, rc_config[key])
            else:  # assume the key is a list-type
                # Note, since conda config --add prepends, these are printed in
                # the reverse order so that entering them in this order will
                # recreate the same file
                items = rc_config.get(key, [])
                numitems = len(items)
                for q, item in enumerate(reversed(items)):
                    # Use repr so that it can be pasted back in to conda config --add
                    if key == "channels" and q in (0, numitems-1):
                        print("--add", key, repr(item),
                              "  # lowest priority" if q == 0 else "  # highest priority")
                    else:
                        print("--add", key, repr(item))

    if args.stdin:
        content = timeout(5, sys.stdin.read)
        if not content:
            return
        try:
            parsed = yaml_load(content)
            rc_config.update(parsed)
        except Exception:  # pragma: no cover
            from ..exceptions import ParseError
            raise ParseError("invalid yaml content:\n%s" % content)

    # prepend, append, add
    for arg, prepend in zip((args.prepend, args.append), (True, False)):
        for key, item in arg:
            if key == 'channels' and key not in rc_config:
                rc_config[key] = ['defaults']
            if key not in sequence_parameters:
                from ..exceptions import CondaValueError
                raise CondaValueError("Key '%s' is not a known sequence parameter." % key)
            if not isinstance(rc_config.get(key, []), list):
                from ..exceptions import CouldntParseError
                bad = rc_config[key].__class__.__name__
                raise CouldntParseError("key %r should be a list, not %s." % (key, bad))
            arglist = rc_config.setdefault(key, [])
            if item in arglist:
                # Right now, all list keys should not contain duplicates
                message = "Warning: '%s' already in '%s' list, moving to the %s" % (
                    item, key, "top" if prepend else "bottom")
                arglist = rc_config[key] = [p for p in arglist if p != item]
                if not context.json:
                    print(message, file=sys.stderr)
                else:
                    json_warnings.append(message)
            arglist.insert(0 if prepend else len(arglist), item)

    # Set
    for key, item in args.set:
        key, subkey = key.split('.', 1) if '.' in key else (key, None)
        if key in primitive_parameters:
            value = context.typify_parameter(key, item)
            rc_config[key] = value
        elif key in map_parameters:
            argmap = rc_config.setdefault(key, {})
            argmap[subkey] = item
        else:
            from ..exceptions import CondaValueError
            raise CondaValueError("Key '%s' is not a known primitive parameter." % key)

    # Remove
    for key, item in args.remove:
        key, subkey = key.split('.', 1) if '.' in key else (key, None)
        if key not in rc_config:
            if key != 'channels':
                from ..exceptions import CondaKeyError
                raise CondaKeyError(key, "key %r is not in the config file" % key)
            rc_config[key] = ['defaults']
        if item not in rc_config[key]:
            from ..exceptions import CondaKeyError
            raise CondaKeyError(key, "%r is not in the %r key of the config file" %
                                (item, key))
        rc_config[key] = [i for i in rc_config[key] if i != item]

    # Remove Key
    for key, in args.remove_key:
        key, subkey = key.split('.', 1) if '.' in key else (key, None)
        if key not in rc_config:
            from ..exceptions import CondaKeyError
            raise CondaKeyError(key, "key %r is not in the config file" %
                                key)
        del rc_config[key]

    # config.rc_keys
    if not args.get:

        # Add representers for enums.
        # Because a representer cannot be added for the base Enum class (it must be added for
        # each specific Enum subclass), and because of import rules), I don't know of a better
        # location to do this.
        def enum_representer(dumper, data):
            return dumper.represent_str(str(data))

        yaml.representer.RoundTripRepresenter.add_representer(SafetyChecks, enum_representer)
        yaml.representer.RoundTripRepresenter.add_representer(PathConflict, enum_representer)

        try:
            with open(rc_path, 'w') as rc:
                rc.write(yaml_dump(rc_config))
        except (IOError, OSError) as e:
            raise CondaError('Cannot write to condarc file at %s\n'
                             'Caused by %r' % (rc_path, e))

    if context.json:
        from .common import stdout_json_success
        stdout_json_success(
            rc_path=rc_path,
            warnings=json_warnings,
            get=json_get
        )
    return
