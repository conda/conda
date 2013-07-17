# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
import re
from argparse import RawDescriptionHelpFormatter

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
        help = """write to the system .condarc file ({system}). Otherwise writes to the user
        config file ({user}).""".format(system=config.sys_rc_path, user=config.user_rc_path),
        )
    location.add_argument(
        "--file",
        action = "store",
        help = """write to the given file. Otherwise writes to the user config file
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
        )
    action.add_argument(
        "--add",
        nargs = 2,
        action = "append",
        help = """add one configuration value to a list key. The default
        behavior is to prepend.""",
        default = [],
        metavar = ('KEY', 'VALUE'),
        )
    action.add_argument(
        "--set",
        nargs = 2,
        action = "append",
        help = "set a boolean key. BOOL_VALUE should be 'yes' or 'no'",
        default = [],
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
        raise RuntimeError("pyyaml is required to modify configuration")

    if args.system:
        rc_path = config.sys_rc_path
    elif args.file:
        rc_path = args.file
    else:
        rc_path = config.user_rc_path

    # Create the file if it doesn't exist
    with open(rc_path, 'r+') as rc:
        rc_text = rc.read()
    rc_config = yaml.load(rc_text)
    if rc_config is None:
        rc_config = {}

    # Get
    if args.get == []:
        args.get = config.rc_list_keys + config.rc_bool_keys
    for key in args.get:
        if key not in config.rc_list_keys + config.rc_bool_keys:
            print "%s is not a valid key" % key
        if key not in rc_config:
            continue
        if isinstance(rc_config[key], bool):
            print "--set", key, rc_config[key]
        else:
            # Note, since conda config --add prepends, these are printed in
            # the reverse order so that entering them in this order will
            # recreate the same file
            for item in reversed(rc_config.get(key, [])):
                # Use repr so that it can be pasted back in to conda config --add
                print "--add", key, repr(item)


    # PyYaml does not support round tripping, so if we use yaml.dump, it
    # will clear all comments and structure from the configuration file.
    # There are no yaml parsers that do this.  Our best bet is to do a
    # simple parsing of the file ourselves.  We can check the result at
    # the end to see if we did it right.

    # First, do it the pyyaml way
    new_rc_config = rc_config.copy()

    # Add
    for key, item in args.add:
        new_rc_config.setdefault(key, []).insert(0, item)

    # Set
    for key, item in args.set:
        yamlitem = yaml.load(item)
        if not isinstance(yamlitem, bool):
            raise RuntimeError("%s is not a boolean" % item)

        new_rc_config[key] = yamlitem

    # Remove
    for key, item in args.remove:
        if key not in new_rc_config:
            raise RuntimeError("key %s is not in the config file" % repr(key))
        if item not in new_rc_config[key]:
            raise RuntimeError("%s is not in the %s key of the config file" %
                (repr(item), repr(key)))
        new_rc_config[key] = [i for i in new_rc_config[key] if i != item]

    # Remove Key
    for key, in args.remove_key:
        if key not in new_rc_config:
            raise RuntimeError("key %s is not in the config file" % key)
        del new_rc_config[key]

    if args.force:
        # Note, force will also remove any checking that the keys are in
        # config.rc_keys
        with open(rc_path, 'w') as rc:
            rc.write(yaml.dump(new_rc_config))
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
            raise RuntimeError("key must be one of %s, not %s" %
                (config.rc_list_keys, key))
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

    for key, item in args.set:
        if key not in config.rc_bool_keys:
            raise RuntimeError("key must be one of %s, not %s" %
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
            parsed_new_rc_text = yaml.load('\n'.join(new_rc_text))
        except yaml.parser.ParserError:
            raise CouldntParse("couldn't parse modified yaml")
        else:
            if not parsed_new_rc_text == new_rc_config:
                print parsed_new_rc_text
                print new_rc_config
                raise CouldntParse("modified yaml doesn't match what it should be")


    if args.add or args.set:
        with open(rc_path, 'w') as rc:
            rc.write('\n'.join(new_rc_text))
