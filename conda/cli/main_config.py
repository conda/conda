# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
from __future__ import absolute_import, division, print_function, unicode_literals

from argparse import SUPPRESS
import collections
import json
import os
from os.path import isfile, join
import sys
from textwrap import wrap

from .conda_argparse import add_parser_json
from .. import CondaError
from ..base.constants import CONDA_HOMEPAGE_URL
from ..base.context import context
from ..common.compat import isiterable, iteritems, string_types, text_type
from ..common.configuration import pretty_list, pretty_map
from ..common.constants import NULL
from ..common.serialize import yaml_dump, yaml_load
from ..config import rc_other, sys_rc_path, user_rc_path

descr = """
Modify configuration values in .condarc.  This is modeled after the git
config command.  Writes to the user .condarc file (%s) by default.

""" % user_rc_path

# Note, the extra whitespace in the list keys is on purpose. It's so the
# formatting from help2man is still valid YAML (otherwise it line wraps the
# keys like "- conda - defaults"). Technically the parser here still won't
# recognize it because it removes the indentation, but at least it will be
# valid.
additional_descr = """
See `conda config --describe` or %s/docs/config.html
for details on all the options that can go in .condarc.

Examples:

Display all configuration values as calculated and compiled:

    conda config --show

Display all identified configuration sources:

    conda config --show-sources

Describe all available configuration options:

    conda config --describe

Add the conda-canary channel:

    conda config --add channels conda-canary

Set the output verbosity to level 3 (highest):

    conda config --set verbosity 3
""" % CONDA_HOMEPAGE_URL


# Note, the formatting of this is designed to work well with help2man
example = """
Examples:

Get the channels defined in the system .condarc:

    conda config --get channels --system

Add the 'foo' Binstar channel:

    conda config --add channels foo

Disable the 'show_channel_urls' option:

    conda config --set show_channel_urls no
"""


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'config',
        description=descr,
        help=descr,
        epilog=additional_descr,
    )
    add_parser_json(p)

    # TODO: use argparse.FileType
    location = p.add_mutually_exclusive_group()
    location.add_argument(
        "--system",
        action="store_true",
        help="""Write to the system .condarc file ({system}). Otherwise writes to the user
        config file ({user}).""".format(system=sys_rc_path,
                                        user=user_rc_path),
    )
    location.add_argument(
        "--env",
        action="store_true",
        help="Write to the active conda environment .condarc file (%s). "
             "If no environment is active, write to the user config file (%s)."
             "" % (os.getenv('CONDA_PREFIX', "<no active environment>"), user_rc_path),
    )
    location.add_argument(
        "--file",
        action="store",
        help="""Write to the given file. Otherwise writes to the user config file ({user})
or the file path given by the 'CONDARC' environment variable, if it is set
(default: %(default)s).""".format(user=user_rc_path),
        default=os.environ.get('CONDARC', user_rc_path)
    )

    # XXX: Does this really have to be mutually exclusive. I think the below
    # code will work even if it is a regular group (although combination of
    # --add and --remove with the same keys will not be well-defined).
    action = p.add_mutually_exclusive_group(required=True)
    action.add_argument(
        "--show",
        action="store_true",
        help="Display all configuration values as calculated and compiled.",
    )
    action.add_argument(
        "--show-sources",
        action="store_true",
        help="Display all identified configuration sources.",
    )
    action.add_argument(
        "--validate",
        action="store_true",
        help="Validate all configuration sources.",
    )
    action.add_argument(
        "--describe",
        action="store_true",
        help="Describe available configuration parameters.",
    )
    action.add_argument(
        "--write-default",
        action="store_true",
        help="Write the default configuration to a file. "
             "Equivalent to `conda config --describe > ~/.condarc` "
             "when no --env, --system, or --file flags are given.",
    )
    action.add_argument(
        "--get",
        nargs='*',
        action="store",
        help="Get a configuration value.",
        default=None,
        metavar='KEY',
    )
    action.add_argument(
        "--append",
        nargs=2,
        action="append",
        help="""Add one configuration value to the end of a list key.""",
        default=[],
        metavar=('KEY', 'VALUE'),
    )
    action.add_argument(
        "--prepend", "--add",
        nargs=2,
        action="append",
        help="""Add one configuration value to the beginning of a list key.""",
        default=[],
        metavar=('KEY', 'VALUE'),
    )
    action.add_argument(
        "--set",
        nargs=2,
        action="append",
        help="""Set a boolean or string key""",
        default=[],
        metavar=('KEY', 'VALUE'),
    )
    action.add_argument(
        "--remove",
        nargs=2,
        action="append",
        help="""Remove a configuration value from a list key. This removes
    all instances of the value.""",
        default=[],
        metavar=('KEY', 'VALUE'),
    )
    action.add_argument(
        "--remove-key",
        nargs=1,
        action="append",
        help="""Remove a configuration key (and all its values).""",
        default=[],
        metavar="KEY",
    )
    action.add_argument(
        "--stdin",
        action="store_true",
        help="Apply configuration information given in yaml format piped through stdin.",
    )

    p.add_argument(
        "-f", "--force",
        action="store_true",
        default=NULL,
        help=SUPPRESS,  # TODO: No longer used.  Remove in a future release.
    )

    p.set_defaults(func=execute)


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
    from .._vendor.auxlib.entity import EntityEncoder
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
    try:
        from cytoolz.itertoolz import concat, groupby
    except ImportError:  # pragma: no cover
        from .._vendor.toolz.itertoolz import concat, groupby  # NOQA
    from .._vendor.auxlib.entity import EntityEncoder

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

    if args.show:
        from collections import OrderedDict

        d = OrderedDict((key, getattr(context, key))
                        for key in context.list_parameters())
        if context.json:
            print(json.dumps(d, sort_keys=True, indent=2, separators=(',', ': '),
                  cls=EntityEncoder))
        else:
            # coerce channels
            d['custom_channels'] = {k: text_type(v).replace(k, '')  # TODO: the replace here isn't quite right  # NOQA
                                    for k, v in iteritems(d['custom_channels'])}
            # TODO: custom_multichannels needs better formatting
            d['custom_multichannels'] = {k: json.dumps([text_type(c) for c in chnls])
                                         for k, chnls in iteritems(d['custom_multichannels'])}

            print('\n'.join(format_dict(d)))
        context.validate_configuration()
        return

    if args.describe:
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
                if key not in rc_other:
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
        content = sys.stdin.read()
        try:
            parsed = yaml_load(content)
        except Exception:  # pragma: no cover
            from ..exceptions import ParseError
            raise ParseError("invalid yaml content:\n%s" % content)
        rc_config.update(parsed)

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
            if key == 'default_channels' and rc_path != sys_rc_path:
                msg = "'default_channels' is only configurable for system installs"
                raise NotImplementedError(msg)
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
