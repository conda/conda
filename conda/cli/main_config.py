# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
from __future__ import absolute_import, division, print_function, unicode_literals

import collections
import json
import os
import sys

from .common import Completer, add_parser_json, stdout_json_success
from .. import CondaError
from .._vendor.auxlib.compat import isiterable
from .._vendor.auxlib.entity import EntityEncoder
from .._vendor.auxlib.type_coercion import boolify
from ..base.constants import CONDA_HOMEPAGE_URL
from ..base.context import context
from ..common.compat import iteritems, string_types
from ..common.configuration import pretty_list, pretty_map
from ..common.constants import NULL
from ..common.yaml import yaml_dump, yaml_load
from ..config import (rc_bool_keys, rc_list_keys, rc_other, rc_string_keys, sys_rc_path,
                      user_rc_path)
from ..exceptions import CondaKeyError, CondaValueError, CouldntParseError

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
See %s/docs/config.html for details on all the options
that can go in .condarc.

List keys, like

  channels:
    - conda
    - defaults

are modified with the --add and --remove options. For example

    conda config --add channels r

on the above configuration would prepend the key 'r', giving

    channels:
      - r
      - conda
      - defaults

Note that the key 'channels' implicitly contains the key 'defaults' if it has
not been configured yet.

Boolean keys, like

    always_yes: true

are modified with --set and removed with --remove-key. For example

    conda config --set always_yes false

gives

    always_yes: false

Note that in YAML, "yes", "YES", "on", "true", "True", and "TRUE" are all
valid ways to spell "true", and "no", "NO", "off", "false", "False", and
"FALSE", are all valid ways to spell "false".

The .condarc file is YAML, and any valid YAML syntax is allowed.
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


class SingleValueKey(Completer):
    def _get_items(self):
        return rc_bool_keys + \
               rc_string_keys + \
               ['yes', 'no', 'on', 'off', 'true', 'false']


class ListKey(Completer):
    def _get_items(self):
        return rc_list_keys


class BoolOrListKey(Completer):
    def __contains__(self, other):
        return other in self.get_items()

    def _get_items(self):
        return rc_list_keys + rc_bool_keys


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'config',
        description=descr,
        help=descr,
        epilog=additional_descr + example,
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
        "--get",
        nargs='*',
        action="store",
        help="Get a configuration value.",
        default=None,
        metavar='KEY',
        choices=BoolOrListKey()
    )
    action.add_argument(
        "--append",
        nargs=2,
        action="append",
        help="""Add one configuration value to the end of a list key.""",
        default=[],
        choices=ListKey(),
        metavar=('KEY', 'VALUE'),
    )
    action.add_argument(
        "--prepend", "--add",
        nargs=2,
        action="append",
        help="""Add one configuration value to the beginning of a list key.""",
        default=[],
        choices=ListKey(),
        metavar=('KEY', 'VALUE'),
    )
    action.add_argument(
        "--set",
        nargs=2,
        action="append",
        help="""Set a boolean or string key""",
        default=[],
        choices=SingleValueKey(),
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

    p.add_argument(
        "-f", "--force",
        action="store_true",
        default=NULL,
        help="""Write to the config file using the yaml parser.  This will
        remove any comments or structure from the file."""
    )

    p.set_defaults(func=execute)


def execute(args, parser):
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

    if args.show:
        from collections import OrderedDict
        d = OrderedDict((key, getattr(context, key))
                        for key in sorted(('add_anaconda_token',
                                           'add_pip_as_python_dependency',
                                           'allow_softlinks',
                                           'always_copy',
                                           'always_softlink',
                                           'always_yes',
                                           'auto_update_conda',
                                           'binstar_upload',
                                           'changeps1',
                                           'channel_alias',
                                           'channel_priority',
                                           'channels',
                                           'client_ssl_cert',
                                           'client_ssl_cert_key',
                                           'create_default_packages',
                                           'debug',
                                           'default_channels',
                                           'disallow',
                                           'envs_dirs',
                                           'json',
                                           'offline',
                                           'proxy_servers',
                                           'quiet',
                                           'shortcuts',
                                           'show_channel_urls',
                                           'ssl_verify',
                                           'track_features',
                                           'update_dependencies',
                                           'use_pip',
                                           'verbosity',
                                           )))
        if context.json:
            print(json.dumps(d, sort_keys=True, indent=2, separators=(',', ': '),
                  cls=EntityEncoder))
        else:
            print('\n'.join(format_dict(d)))
        context.validate_configuration()
        return

    if args.validate:
        context.validate_all()
        return

    if args.system:
        rc_path = sys_rc_path
    elif args.file:
        rc_path = args.file
    else:
        rc_path = user_rc_path

    # read existing condarc
    if os.path.exists(rc_path):
        with open(rc_path, 'r') as fh:
            rc_config = yaml_load(fh) or {}
    else:
        rc_config = {}

    # Get
    if args.get is not None:
        context.validate_all()
        if args.get == []:
            args.get = sorted(rc_config.keys())
        for key in args.get:
            if key not in rc_list_keys + rc_bool_keys + rc_string_keys:
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

    # prepend, append, add
    for arg, prepend in zip((args.prepend, args.append), (True, False)):
        for key, item in arg:
            if key == 'channels' and key not in rc_config:
                rc_config[key] = ['defaults']
            if key not in rc_list_keys:
                raise CondaValueError("key must be one of %s, not %r" %
                                      (', '.join(rc_list_keys), key))
            if not isinstance(rc_config.get(key, []), list):
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
    set_bools, set_strings = set(rc_bool_keys), set(rc_string_keys)
    for key, item in args.set:
        # Check key and value
        if key in set_bools:
            rc_config[key] = boolify(item)
        elif key in set_strings:
            assert isinstance(item, string_types)
            rc_config[key] = item
        elif key == 'ssl_verify':
            rc_config[key] = boolify(item, return_string=True)
        else:
            raise CondaValueError("Error key must be one of %s, not %s" %
                                  (', '.join(set_bools | set_strings), key))

    # Remove
    for key, item in args.remove:
        if key not in rc_config:
            if key != 'channels':
                raise CondaKeyError(key, "key %r is not in the config file" % key)
            rc_config[key] = ['defaults']
        if item not in rc_config[key]:
            raise CondaKeyError(key, "%r is not in the %r key of the config file" %
                                (item, key))
        rc_config[key] = [i for i in rc_config[key] if i != item]

    # Remove Key
    for key, in args.remove_key:
        if key not in rc_config:
            raise CondaKeyError(key, "key %r is not in the config file" %
                                key)
        del rc_config[key]

    # config.rc_keys
    with open(rc_path, 'w') as rc:
        rc.write(yaml_dump(rc_config))

    if context.json:
        stdout_json_success(
            rc_path=rc_path,
            warnings=json_warnings,
            get=json_get
        )
    return
