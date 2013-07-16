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
    conda config --add channels foo
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
        help = ("write to the system .condarc file (%s)" %
            config.sys_rc_path),
        )
    location.add_argument(
        "--file",
        action = "store",
        help = "write to the given file",
        )

    action = p.add_mutually_exclusive_group(required=True)
    action.add_argument(
        "--get",
        nargs = 1,
        action = "append",
        help = "get the configuration value",
        default = []
        )
    action.add_argument(
        "--add",
        nargs = 2,
        action = "append",
        help = "add one configuration value. The default is to prepend.",
        default = []
        )
    p.set_defaults(func=execute)

    p.add_argument(
        "-f", "--force",
        action = "store_true",
        help = """Write to the config file using the yaml parser.  This will
        remove any comments or structure from the file."""
        )

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

    with open(rc_path, 'r') as rc:
        rc_text = rc.read()
    rc_config = yaml.load(rc_text)

    # Get
    for key, in args.get:
        for item in rc_config.get(key, []):
            # Use repr so that it can be pasted back in to conda config --add
            print key, repr(item)

    # Add

    # PyYaml does not support round tripping, so if we use yaml.dump, it
    # will clear all comments and structure from the configuration file.
    # There are no yaml parsers that do this.  Our best bet is to do a
    # simple parsing of the file ourselves.  We can check the result at
    # the end to see if we did it right.

    # First, do it the pyyaml way

    new_rc_config = rc_config.copy()
    for key, item in args.add:
        new_rc_config.setdefault(key, []).insert(0, item)

    if args.force:
        # Note, force will also remove any checking that the keys are in
        # config.rc_keys
        with open(rc_path, 'w') as rc:
            rc.write(yaml.dump(new_rc_config))
        return

    # Now, try to parse the condarc file.

    # Just support "   key:  " for now
    keyregexes = {key:re.compile(r"( *)%s *" % key)
        for key in dict(args.add)
        }

    new_rc_text = rc_text[:].split("\n")
    for key, item in args.add:
        if key not in config.rc_keys:
            raise ValueError("key must be one of %s, not %s" %
                (config.rc_keys, key))
        added = False
        for pos, line in enumerate(new_rc_text[:]):
            matched = keyregexes[key].match(line)
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


    if args.add:
        # Verify that the new rc text parses to the same thing as if we had
        # used yaml.
        try:
            parsed_new_rc_text = yaml.load('\n'.join(new_rc_text))
        except yaml.parser.ParserError:
            raise CouldntParse("couldn't parse modified yaml")
        else:
            if not parsed_new_rc_text == new_rc_config:
                raise CouldntParse("modified yaml doesn't match what it should be")



    if args.add:
        with open(rc_path, 'w') as rc:
            rc.write('\n'.join(new_rc_text))
