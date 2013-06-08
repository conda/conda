# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

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
        help = "add one configuration value",
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
        rc_config = yaml.load(rc)

    for key, in args.get:
        for item in rc_config.get(key, []):
            # Use repr so that it can be pasted back in
            print key, repr(item)

    for key, item in args.add:
        rc_config.setdefault(key, []).append(item)

    if args.add:
        with open(rc_path, 'w') as rc:
            rc.write(yaml.dump(rc_config))
