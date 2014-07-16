# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
from __future__ import print_function, division, absolute_import

import re
import os
import sys
from argparse import RawDescriptionHelpFormatter
from copy import deepcopy

import conda.config as config

descr = """
Modify configuration values in .condarc.  This is modeled after the git
config command.  Writes to the user .condarc file (%s) by default.
""" % config.user_rc_path

example = """
examples:
    conda config --get channels --system
    conda config --add channels http://conda.binstar.org/foo
"""

class CouldntParse(NotImplementedError):
    def __init__(self, reason):
        self.args = ["""Could not parse the yaml file. Use -f to use the
yaml parser (this will remove any structure or comments from the existing
.condarc file). Reason: %s""" % reason]

class BoolKey(object):
    def __contains__(self, other):
        # Other is either one of the keys or the boolean
        try:
            import yaml
        except ImportError:
            yaml = False

        ret = other in config.rc_bool_keys
        if yaml:
            ret = ret or isinstance(yaml.load(other), bool)

        return ret

    def __iter__(self):
        for i in config.rc_bool_keys + ['yes', 'no', 'on', 'off', 'true', 'false']:
            yield i

class ListKey(object):
    def __contains__(self, other):
        # We can't check the elements of the list themselves
        return True

    def __iter__(self):
        for i in config.rc_list_keys:
            yield i

class BoolOrListKey(object):
    def __contains__(self, other):
        return other in config.rc_bool_keys or other in config.rc_list_keys

    def __iter__(self):
        for i in config.rc_list_keys:
            yield i
        for i in config.rc_bool_keys:
            yield i

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'config',
        formatter_class = RawDescriptionHelpFormatter,
        description = descr,
        help = descr,
        epilog = example,
        )

    # TODO: use argparse.FileType
    location = p.add_mutually_exclusive_group()
    location.add_argument(
        "--system",
        action = "store_true",
        help = """\
write to the system .condarc file ({system}). Otherwise writes to the user
        config file ({user}).""".format(system=config.sys_rc_path,
                                        user=config.user_rc_path),
        )
    location.add_argument(
        "--file",
        action = "store",
        help = """\
write to the given file. Otherwise writes to the user config file
        ({user}).""".format(user=config.user_rc_path),
        )

    # XXX: Does this really have to be mutually exclusive. I think the below
    # code will work even if it is a regular group (although combination of
    # --add and --remove with the same keys will not be well-defined).
    action = p.add_mutually_exclusive_group(required=True)
    action.add_argument(
        "--get",
        nargs = '*',
        action = "store",
        help = "get the configuration value",
        default = None,
        metavar = ('KEY'),
        choices=BoolOrListKey()
        )
    action.add_argument(
        "--add",
        nargs = 2,
        action = "append",
        help = """add one configuration value to a list key. The default
        behavior is to prepend.""",
        default = [],
        choices=ListKey(),
        metavar = ('KEY', 'VALUE'),
        )
    action.add_argument(
        "--set",
        nargs = 2,
        action = "append",
        help = "set a boolean key. BOOL_VALUE should be 'yes' or 'no'",
        default = [],
        choices=BoolKey(),
        metavar = ('KEY', 'BOOL_VALUE'),
        )
    action.add_argument(
        "--remove",
        nargs = 2,
        action = "append",
        help = """remove a configuration value from a list key. This removes
    all instances of the value""",
        default = [],
        metavar = ('KEY', 'VALUE'),
        )
    action.add_argument(
        "--remove-key",
        nargs = 1,
        action = "append",
        help = """remove a configuration key (and all its values)""",
        default = [],
        metavar = "KEY",
        )

    p.add_argument(
        "-f", "--force",
        action = "store_true",
        help = """Write to the config file using the yaml parser.  This will
        remove any comments or structure from the file."""
        )

    p.set_defaults(func=execute)


def execute(args, parser):
    try:
        import yaml
    except ImportError:
        sys.exit("Error: pyyaml is required to modify configuration")

    if args.system:
        rc_path = config.sys_rc_path
    elif args.file:
        rc_path = args.file
    else:
        rc_path = config.user_rc_path

    # Create the file if it doesn't exist
    if not os.path.exists(rc_path):
        if args.add and 'channels' in list(zip(*args.add))[0] and not ['channels', 'defaults'] in args.add:
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
    rc_config = yaml.load(rc_text)
    if rc_config is None:
        rc_config = {}

    # Get
    if args.get is not None:
        if args.get == []:
            args.get = sorted(rc_config.keys())
        for key in args.get:
            if key not in config.rc_list_keys + config.rc_bool_keys:
                if key not in config.rc_other:
                    print("%s is not a valid key" % key, file=sys.stderr)
                continue
            if key not in rc_config:
                continue
            if isinstance(rc_config[key], bool):
                print("--set", key, rc_config[key])
            else:
                # Note, since conda config --add prepends, these are printed in
                # the reverse order so that entering them in this order will
                # recreate the same file
                for item in reversed(rc_config.get(key, [])):
                    # Use repr so that it can be pasted back in to conda config --add
                    print("--add", key, repr(item))


    # PyYaml does not support round tripping, so if we use yaml.dump, it
    # will clear all comments and structure from the configuration file.
    # There are no yaml parsers that do this.  Our best bet is to do a
    # simple parsing of the file ourselves.  We can check the result at
    # the end to see if we did it right.

    # First, do it the pyyaml way
    new_rc_config = deepcopy(rc_config)

    # Add
    for key, item in args.add:
        if item in rc_config.get(key, []):
            # Right now, all list keys should not contain duplicates
            print("Skipping %s: %s, item already exists" % (key, item), file=sys.stderr)
            continue
        new_rc_config.setdefault(key, []).insert(0, item)

    # Set
    for key, item in args.set:
        yamlitem = yaml.load(item)
        if not isinstance(yamlitem, bool):
            sys.exit("Error: %r is not a boolean" % item)

        new_rc_config[key] = yamlitem

    # Remove
    for key, item in args.remove:
        if key not in new_rc_config:
            sys.exit("Error: key %r is not in the config file" % key)
        if item not in new_rc_config[key]:
            sys.exit("Error: %r is not in the %r key of the config file" %
                     (item, key))
        new_rc_config[key] = [i for i in new_rc_config[key] if i != item]

    # Remove Key
    for key, in args.remove_key:
        if key not in new_rc_config:
            sys.exit("Error: key %r is not in the config file" % key)
        del new_rc_config[key]

    if args.force:
        # Note, force will also remove any checking that the keys are in
        # config.rc_keys
        with open(rc_path, 'w') as rc:
            rc.write(yaml.dump(new_rc_config, default_flow_style=False))
        return

    # Now, try to parse the condarc file.

    # Just support "   key:  " for now
    listkeyregexes = {key:re.compile(r"( *)%s *" % key)
        for key in dict(args.add)
        }
    setkeyregexes = {key:re.compile(r"( *)%s( *):( *)" % key)
        for key in dict(args.set)
        }

    new_rc_text = rc_text[:].split("\n")

    for key, item in args.add:
        if key not in config.rc_list_keys:
            sys.exit("Error: key must be one of %s, not %s" %
                     (config.rc_list_keys, key))

        if item in rc_config.get(key, []):
            # Skip duplicates. See above
            continue
        added = False
        for pos, line in enumerate(new_rc_text[:]):
            matched = listkeyregexes[key].match(line)
            if matched:
                leading_space = matched.group(1)
                # TODO: Try to guess how much farther to indent the
                # item. Right now, it is fixed at 2 spaces.
                new_rc_text.insert(pos + 1, "%s  - %s" % (leading_space, item))
                added = True
        if not added:
            if key in rc_config:
                # We should have found it above
                raise CouldntParse("existing list key couldn't be found")
            # TODO: Try to guess the correct amount of leading space for the
            # key. Right now it is zero.
            new_rc_text += ['%s:' % key, '  - %s' % item]
            if key == 'channels' and ['channels', 'defaults'] not in args.add:
                # If channels key is added for the first time, make sure it
                # includes 'defaults'
                new_rc_text += ['  - defaults']
                new_rc_config['channels'].append('defaults')

    for key, item in args.set:
        if key not in config.rc_bool_keys:
            sys.exit("Error key must be one of %s, not %s" %
                     (config.rc_bool_keys, key))
        added = False
        for pos, line in enumerate(new_rc_text[:]):
            matched = setkeyregexes[key].match(line)
            if matched:
                leading_space = matched.group(1)
                precol_space = matched.group(2)
                postcol_space = matched.group(3)
                new_rc_text[pos] = '%s%s%s:%s%s' % (leading_space, key,
                    precol_space, postcol_space, item)
                added = True
        if not added:
            if key in rc_config:
                raise CouldntParse("existing bool key couldn't be found")
            new_rc_text += ['%s: %s' % (key, item)]

    for key, item in args.remove:
        raise NotImplementedError("--remove without --force is not implemented "
            "yet")

    for key, in args.remove_key:
        raise NotImplementedError("--remove-key without --force is not "
            "implemented yet")

    if args.add or args.set:
        # Verify that the new rc text parses to the same thing as if we had
        # used yaml.
        try:
            parsed_new_rc_text = yaml.load('\n'.join(new_rc_text).strip('\n'))
        except yaml.parser.ParserError:
            raise CouldntParse("couldn't parse modified yaml")
        else:
            if not parsed_new_rc_text == new_rc_config:
                raise CouldntParse("modified yaml doesn't match what it "
                                   "should be")

    if args.add or args.set:
        with open(rc_path, 'w') as rc:
            rc.write('\n'.join(new_rc_text).strip('\n'))
            rc.write('\n')
