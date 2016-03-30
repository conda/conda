# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
from __future__ import print_function, division, absolute_import

import os
import sys

import conda.config as config
from conda.cli import common
from conda.compat import string_types
from conda.utils import yaml_load, yaml_dump

descr = """
Modify configuration values in .condarc.  This is modeled after the git
config command.  Writes to the user .condarc file (%s) by default.

""" % config.user_rc_path

# Note, the extra whitespace in the list keys is on purpose. It's so the
# formatting from help2man is still valid YAML (otherwise it line wraps the
# keys like "- conda - defaults"). Technically the parser here still won't
# recognize it because it removes the indentation, but at least it will be
# valid.
additional_descr = """
See http://conda.pydata.org/docs/config.html for details on all the options
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
"""


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

class CouldntParse(NotImplementedError):
    def __init__(self, reason):
        self.args = ["""Could not parse the yaml file. Use -f to use the
yaml parser (this will remove any structure or comments from the existing
.condarc file). Reason: %s""" % reason]

class SingleValueKey(common.Completer):
    def _get_items(self):
        return config.rc_bool_keys + \
               config.rc_string_keys + \
               ['yes', 'no', 'on', 'off', 'true', 'false']

class ListKey(common.Completer):
    def _get_items(self):
        return config.rc_list_keys

class BoolOrListKey(common.Completer):
    def __contains__(self, other):
        return other in self.get_items()

    def _get_items(self):
        return config.rc_list_keys + config.rc_bool_keys

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'config',
        description=descr,
        help=descr,
        epilog=additional_descr + example,
        )
    common.add_parser_json(p)

    # TODO: use argparse.FileType
    location = p.add_mutually_exclusive_group()
    location.add_argument(
        "--system",
        action="store_true",
        help="""Write to the system .condarc file ({system}). Otherwise writes to the user
        config file ({user}).""".format(system=config.sys_rc_path,
                                        user=config.user_rc_path),
        )
    location.add_argument(
        "--file",
        action="store",
        help="""Write to the given file. Otherwise writes to the user config file ({user})
or the file path given by the 'CONDARC' environment variable, if it is set
(default: %(default)s).""".format(user=config.user_rc_path),
        default=os.environ.get('CONDARC', config.user_rc_path)
        )

    # XXX: Does this really have to be mutually exclusive. I think the below
    # code will work even if it is a regular group (although combination of
    # --add and --remove with the same keys will not be well-defined).
    action = p.add_mutually_exclusive_group(required=True)
    action.add_argument(
        "--get",
        nargs='*',
        action="store",
        help="Get a configuration value.",
        default=None,
        metavar=('KEY'),
        choices=BoolOrListKey()
        )
    action.add_argument(
        "--add",
        nargs=2,
        action="append",
        help="""Add one configuration value to a list key. The default
        behavior is to prepend.""",
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
        help="""Write to the config file using the yaml parser.  This will
        remove any comments or structure from the file."""
        )

    p.set_defaults(func=execute)


def execute(args, parser):
    try:
        execute_config(args, parser)
    except (CouldntParse, NotImplementedError) as e:
        if args.json:
            common.exception_and_exit(e, json=True)
        else:
            raise


def execute_config(args, parser):
    json_warnings = []
    json_get = {}

    if args.system:
        rc_path = config.sys_rc_path
    elif args.file:
        rc_path = args.file
    else:
        rc_path = config.user_rc_path

    # Create the file if it doesn't exist
    if not os.path.exists(rc_path):
        has_defaults = ['channels', 'defaults'] in args.add
        if args.add and 'channels' in list(zip(*args.add))[0] and not has_defaults:
            # If someone adds a channel and their .condarc doesn't exist, make
            # sure it includes the defaults channel, or else they will end up
            # with a broken conda.
            rc_text = """\
channels:
  - defaults
"""
        else:
            rc_text = ""
    else:
        with open(rc_path, 'r') as rc:
            rc_text = rc.read()
    rc_config = yaml_load(rc_text)
    if rc_config is None:
        rc_config = {}

    # Get
    if args.get is not None:
        if args.get == []:
            args.get = sorted(rc_config.keys())
        for key in args.get:
            if key not in config.rc_list_keys + config.rc_bool_keys + config.rc_string_keys:
                if key not in config.rc_other:
                    message = "unknown key %s" % key
                    if not args.json:
                        print(message, file=sys.stderr)
                    else:
                        json_warnings.append(message)
                continue
            if key not in rc_config:
                continue

            if args.json:
                json_get[key] = rc_config[key]
                continue

            if isinstance(rc_config[key], (bool, string_types)):
                print("--set", key, rc_config[key])
            else:
                # Note, since conda config --add prepends, these are printed in
                # the reverse order so that entering them in this order will
                # recreate the same file
                for item in reversed(rc_config.get(key, [])):
                    # Use repr so that it can be pasted back in to conda config --add
                    print("--add", key, repr(item))

    # Add
    for key, item in args.add:
        if key not in config.rc_list_keys:
            common.error_and_exit("key must be one of %s, not %r" %
                                  (', '.join(config.rc_list_keys), key), json=args.json,
                                  error_type="ValueError")
        if not isinstance(rc_config.get(key, []), list):
            bad = rc_config[key].__class__.__name__
            raise CouldntParse("key %r should be a list, not %s." % (key, bad))
        if key == 'default_channels' and rc_path != config.sys_rc_path:
            msg = "'default_channels' is only configurable for system installs"
            raise NotImplementedError(msg)
        if item in rc_config.get(key, []):
            # Right now, all list keys should not contain duplicates
            message = "Skipping %s: %s, item already exists" % (key, item)
            if not args.json:
                print(message, file=sys.stderr)
            else:
                json_warnings.append(message)
            continue
        rc_config.setdefault(key, []).insert(0, item)

    # Set
    set_bools, set_strings = set(config.rc_bool_keys), set(config.rc_string_keys)
    for key, item in args.set:
        # Check key and value
        yamlitem = yaml_load(item)
        if key in set_bools:
            if not isinstance(yamlitem, bool):
                common.error_and_exit("Key: %s; %s is not a YAML boolean." % (key, item),
                                      json=args.json, error_type="TypeError")
            rc_config[key] = yamlitem
        elif key in set_strings:
            rc_config[key] = yamlitem
        else:
            common.error_and_exit("Error key must be one of %s, not %s" %
                                  (', '.join(set_bools | set_strings), key), json=args.json,
                                  error_type="ValueError")

    # Remove
    for key, item in args.remove:
        if key not in rc_config:
            common.error_and_exit("key %r is not in the config file" % key, json=args.json,
                                  error_type="KeyError")
        if item not in rc_config[key]:
            common.error_and_exit("%r is not in the %r key of the config file" %
                                  (item, key), json=args.json, error_type="KeyError")
        rc_config[key] = [i for i in rc_config[key] if i != item]

    # Remove Key
    for key, in args.remove_key:
        if key not in rc_config:
            common.error_and_exit("key %r is not in the config file" % key, json=args.json,
                                  error_type="KeyError")
        del rc_config[key]

    # config.rc_keys
    with open(rc_path, 'w') as rc:
        rc.write(yaml_dump(rc_config))

    if args.json:
        common.stdout_json_success(
            rc_path=rc_path,
            warnings=json_warnings,
            get=json_get
        )
    return
