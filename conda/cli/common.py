from __future__ import print_function, division, absolute_import

import os
import sys
import argparse
import urlparse
from os.path import abspath, basename, expanduser, isdir, join

import conda.config as config


def add_parser_prefix(p):
    npgroup = p.add_mutually_exclusive_group()
    npgroup.add_argument(
        '-n', "--name",
        action = "store",
        help = "name of environment (in %s)" %
                            os.pathsep.join(config.envs_dirs),
    )
    npgroup.add_argument(
        '-p', "--prefix",
        action = "store",
        help = "full path to environment prefix (default: %s)" %
                                           config.default_prefix,
        metavar = 'PATH',
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

def add_parser_channels(p, dashc=True):
    channel_args = ("--channel",)
    if dashc:
        channel_args = ('-c',) + channel_args
    p.add_argument(*channel_args,
        action = "append",
        help = """additional channel to search for packages. These are searched in the order
        they are given, and then the defaults or channels from .condarc
        (unless --override-channels is given).  You can use 'defaults' to get
        the default packages for conda, and 'system' to get the system
        packages, which also takes .condarc into account. """ # we can't put , here; invalid syntax
    )
    p.add_argument(
        "--override-channels",
        action = "store_true",
        help = """Do not search default or .condarc channels.  Requires --channel.""",
    )


def is_url(url):
    return urlparse.urlparse(url).scheme != ""


# Add http://conda.binstar.org/ to any channel that 
#  does not already have 'default' or 'system' or 'http[s]://' in the name.
def fix_channel_arg(args):
    if not args.channel:
        return
    newlist = []
    for channel in args.channel:
        if not (channel in ['defaults', 'system'] or is_url(channel)):
            newlist.append('http://conda.binstar.org/' + channel)
        else:
            newlist.append(channel)
    args.channel = newlist

def ensure_override_channels_requires_channel(args, dashc=True):
    if args.override_channels and not args.channel:
        if dashc:
            sys.exit('Error: --override-channels requires -c/--channel')
        else:
            sys.exit('Error: --override-channels requires --channel')
    fix_channel_arg(args)

def confirm(args, message="Proceed", choices=('yes', 'no'), default='yes'):
    assert default in choices, default
    if args.dry_run:
        sys.exit(0)

    options = []
    for option in choices:
        if option == default:
            options.append('[%s]' % option[0])
        else:
            options.append(option[0])
    message = "%s (%s)? " % (message, '/'.join(options))
    choices = {alt:choice for choice in choices for alt in [choice,
                                                            choice[0]]}
    choices[''] = default
    while True:
        # raw_input has a bug and prints to stderr, not desirable
        sys.stdout.write(message)
        sys.stdout.flush()
        user_choice = sys.stdin.readline().strip().lower()
        if user_choice not in choices:
            print("Invalid choice: %s" % user_choice)
        else:
            sys.stdout.write("\n")
            sys.stdout.flush()
            return choices[user_choice]


def confirm_yn(args, message="Proceed", default='yes', exit_no=True):
    if args.yes or config.always_yes:
        return True
    try:
        choice = confirm(args, message=message, choices=('yes', 'no'),
                         default=default)
    except KeyboardInterrupt:
        # no need to exit by showing the traceback
        sys.exit("\nOperation aborted.  Exiting.")
    if choice == 'yes':
        return True
    if exit_no:
        sys.exit(1)
    return False

# --------------------------------------------------------------------

def ensure_name_or_prefix(args, command):
    if not (args.name or args.prefix):
        sys.exit('Error: either -n NAME or -p PREFIX option required,\n'
                 '       try "conda %s -h" for more details' % command)

def find_prefix_name(name):
    if name == config.root_env_name:
        return config.root_dir
    for envs_dir in config.envs_dirs:
        prefix = join(envs_dir, name)
        if isdir(prefix):
            return prefix
    return None

def get_prefix(args, search=True):
    if args.name:
        if args.name == config.root_env_name:
            return config.root_dir
        if search:
            prefix = find_prefix_name(args.name)
            if prefix:
                return prefix
        return join(config.envs_dirs[0], args.name)

    if args.prefix:
        return abspath(expanduser(args.prefix))

    return config.default_prefix

def inroot_notwritable(prefix):
    """
    return True if the prefix is under root and root is not writeable
    """
    return (abspath(prefix).startswith(config.root_dir) and
            not config.root_writable)

def name_prefix(prefix):
    if abspath(prefix) == config.root_dir:
        return config.root_env_name
    return basename(prefix)

def check_write(command, prefix):
    if inroot_notwritable(prefix):
        from conda.cli.help import root_read_only

        root_read_only(command, prefix)

# -------------------------------------------------------------------------

def arg2spec(arg):
    parts = arg.split('=')
    name = parts[0].lower()
    for c in ' !@#$%^&*()[]{}|<>?':
        if c in name:
            sys.exit("Error: Invalid character '%s' in package "
                     "name: '%s'" % (c, name))
    if name in config.disallow:
        sys.exit("Error: specification '%s' is disallowed" % name)
    if len(parts) == 1:
        return name
    if len(parts) == 2:
        ver = parts[1]
        if ver.endswith('.0'):
            return '%s %s|%s*' % (name, ver[:-2], ver)
        else:
            return '%s %s*' % (name, ver)
    if len(parts) == 3:
        return '%s %s %s' % (name, parts[1], parts[2])
    sys.exit('Error: Invalid package specification: %s' % arg)


def specs_from_args(args):
    return [arg2spec(arg) for arg in args]


def specs_from_url(url):
    from conda.fetch import TmpDownload

    with TmpDownload(url, verbose=False) as path:
        specs = []
        try:
            for line in open(path):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                specs.append(arg2spec(line))
        except IOError:
            sys.exit('Error: cannot open file: %s' % path)
    return specs


def names_in_specs(names, specs):
    return any(spec.split()[0] in names for spec in specs)


def check_specs(prefix, specs):
    from conda.plan import is_root_prefix

    if len(specs) == 0:
        sys.exit("Error: no package specifications supplied")

    if not is_root_prefix(prefix) and names_in_specs(['conda'], specs):
        sys.exit("Error: Package 'conda' may only be installed in the "
                 "root environment")


def disp_features(features):
    if features:
        return '[%s]' % ' '.join(features)
    else:
        return ''


def stdout_json(d):
    import json

    json.dump(d, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write('\n')

root_no_rm = 'python', 'pycosat', 'pyyaml', 'conda'
