# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
import re

import common
import conda.config as config

descr = """
Modify configuration values in .condarc.  This is modeled after the git
config command.  Writes to the user .condarc file (%s) by default.
""" % config.user_rc_path

example = """
examples:
    conda config -add channels foo
"""

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'config',
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
            # Use repr so that it can be pasted back in
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

    # Now, try to parse the condarc file.

    # Just support "   key:  " for now
    keyregexes = {key:re.compile(r"( *)%s *" % key)
        for key in dict(args.add)
        }

    new_rc_text = rc_text[:].split("\n")
    for key, item in args.add:
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
            raise NotImplementedError("Adding new keys")

    if args.add:
        # Verify that the new rc text parses to the same thing as if we had
        # used yaml.
        try:
            parsed_new_rc_text = yaml.load('\n'.join(new_rc_text))
            parsed = True
        except yaml.parser.ParserError:
            parsed = False
        else:
            parsed = parsed_new_rc_text == new_rc_config

        if not parsed:
            raise NotImplementedError("Could not parse the yaml file")


    if args.add:
        with open(rc_path, 'w') as rc:
            rc.write('\n'.join(new_rc_text))
