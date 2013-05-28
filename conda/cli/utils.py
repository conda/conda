import sys
import argparse
from os.path import abspath, expanduser, join

import conda.config as config


def add_parser_prefix(p):
    npgroup = p.add_mutually_exclusive_group()
    npgroup.add_argument(
        '-n', "--name",
        action = "store",
        help = "name of environment (directory in %s)" % config.envs_dir,
    )
    npgroup.add_argument(
        '-p', "--prefix",
        action = "store",
        help = "full path to environment prefix (default: %s)" %
                                           config.default_prefix,
    )


def add_parser_yes(p):
    p.add_argument(
        "--yes",
        action = "store_true",
        help = "do not ask for confirmation",
    )
    p.add_argument(
        "--dry-run",
        action = "store_true",
        help = "only display what would have been done",
    )


def add_parser_json(p):
    p.add_argument(
        "--json",
        action = "store_true",
        help = argparse.SUPPRESS,
    )


def add_parser_quiet(p):
    p.add_argument(
        '-q', "--quiet",
        action = "store_true",
        help = "do not display progress bar",
    )


def confirm(args):
    if args.dry_run:
        sys.exit(0)
    if args.yes:
        return
    # raw_input has a bug and prints to stderr, not desirable
    print "Proceed (y/n)? ",
    proceed = sys.stdin.readline()
    if proceed.strip().lower() in ('y', 'yes'):
        return
    sys.exit(0)

# --------------------------------------------------------------------

def ensure_name_or_prefix(args, command):
    if not (args.name or args.prefix):
        sys.exit('Error: either -n NAME or -p PREFIX option required,\n'
                 '       try "conda %s -h" for more details' % command)


def get_prefix(args):
    if args.name:
        return join(config.envs_dir, args.name)

    if args.prefix:
        return abspath(expanduser(args.prefix))

    return config.default_prefix


def arg2spec(arg):
    parts = arg.split('=')
    name = parts[0].lower()
    for c in ' !@#$%^&*()[]{}|<>?':
        if c in name:
            sys.exit("Error: Invalid character '%s' in package "
                     "name: '%s'" % (c, name))
    if len(parts) == 1:
        return name
    if len(parts) == 2:
        return '%s %s*' % (name, parts[1])
    if len(parts) == 3:
        return '%s %s %s' % (name, parts[1], parts[2])
    sys.exit('Error: Invalid package specification: %s' % arg)


def specs_from_args(args):
    return [arg2spec(arg) for arg in args]


def specs_from_file(path):
    try:
        specs = []
        for line in open(path):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            specs.append(arg2spec(line))
    except IOError:
        sys.exit('Error: cannot open file: %s' % path)
    return specs


def check_specs(prefix, specs):
    if len(specs) == 0:
        sys.exit("Error: no package specifications supplied")

    if (prefix != config.root_dir and
                 any(s.split()[0] == 'conda' for s in specs)):
        sys.exit("Error: Package 'conda' may only be installed in the "
                 "root environment")


def disp_features(features):
    if features:
        return '[%s]' % ' '.join(features)
    else:
        return ''
