from __future__ import print_function, division, absolute_import

import re
import os
import sys
import argparse
import contextlib
from os.path import abspath, basename, expanduser, isdir, join
import textwrap

import conda.config as config
from conda import console
from conda.utils import memoize
from conda.resolve import MatchSpec


class Completer(object):
    """
    Subclass this class to get tab completion from argcomplete

    There are two ways to use this. One is to subclass and define `_get_items(self)`
    to return a list of all possible completions, and put that as the choices
    in the add_argument. If you do that, you will probably also want to set
    metavar to something, so that the argparse help doesn't show all possible
    choices.

    Another option is to define `_get_items(self)` in the same way, but also
    define `__init__(self, prefix, parsed_args, **kwargs)` (I'm not sure what
    goes in kwargs).  The prefix will be the parsed arguments so far, and
    `parsed_args` will be an argparse args object. Then use

    p.add_argument('argname', ...).completer = TheSubclass

    Use this second option if the set of completions depends on the command
    line flags (e.g., the list of completed packages to install changes if -c
    flags are used).
    """
    @memoize
    def get_items(self):
        return self._get_items()

    def __contains__(self, item):
        # This generally isn't all possibilities, and even if it is, we want
        # to give better error messages than argparse
        return True

    def __iter__(self):
        return iter(self.get_items())

class Environments(Completer):
    def _get_items(self):
        res = []
        for dir in config.envs_dirs:
            try:
                res.extend(os.listdir(dir))
            except OSError:
                pass
        return res

class Packages(Completer):
    def __init__(self, prefix, parsed_args, **kwargs):
        self.prefix = prefix
        self.parsed_args = parsed_args

    def _get_items(self):
        # TODO: Include .tar.bz2 files for local installs.
        from conda.api import get_index
        args = self.parsed_args
        call_dict = dict(channel_urls=args.channel or (),
                         use_cache=True,
                         prepend=not args.override_channels,
                         unknown=args.unknown,
                         offline=args.offline)
        if hasattr(args, 'platform'):  # in search
            call_dict['platform'] = args.platform
        index = get_index(**call_dict)
        return [i.rsplit('-', 2)[0] for i in index]

class InstalledPackages(Completer):
    def __init__(self, prefix, parsed_args, **kwargs):
        self.prefix = prefix
        self.parsed_args = parsed_args

    @memoize
    def _get_items(self):
        import conda.install
        packages = conda.install.linked(get_prefix(self.parsed_args))
        return [i.rsplit('-', 2)[0] for i in packages]

def add_parser_help(p):
    """
    So we can use consistent capitalization and periods in the help. You must
    use the add_help=False argument to ArgumentParser or add_parser to use
    this. Add this first to be consistent with the default argparse output.

    """
    p.add_argument(
        '-h', '--help',
        action=argparse._HelpAction,
        help="Show this help message and exit.",
    )

def add_parser_prefix(p):
    npgroup = p.add_mutually_exclusive_group()
    npgroup.add_argument(
        '-n', "--name",
        action="store",
        help="Name of environment (in %s)." % os.pathsep.join(config.envs_dirs),
        metavar="ENVIRONMENT",
        choices=Environments(),
    )
    npgroup.add_argument(
        '-p', "--prefix",
        action="store",
        help="Full path to environment prefix (default: %s)." %
             config.default_prefix,
        metavar='PATH',
    )


def add_parser_yes(p):
    p.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Do not ask for confirmation.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Only display what would have been done.",
    )


def add_parser_json(p):
    p.add_argument(
        "--json",
        action="store_true",
        help="Report all output as json. Suitable for using conda programmatically."
    )


def add_parser_quiet(p):
    p.add_argument(
        '-q', "--quiet",
        action="store_true",
        help="Do not display progress bar.",
    )

def add_parser_channels(p):
    p.add_argument(
        '-c', '--channel',
        action="append",
        help="""Additional channel to search for packages. These are URLs searched in the order
        they are given (including file:// for local directories).  Then, the defaults
        or channels from .condarc are searched (unless --override-channels is given).  You can use
        'defaults' to get the default packages for conda, and 'system' to get the system
        packages, which also takes .condarc into account.  You can also use any name and the
        .condarc channel_alias value will be prepended.  The default channel_alias
        is http://conda.anaconda.org/.""",
    )
    p.add_argument(
        "--override-channels",
        action="store_true",
        help="""Do not search default or .condarc channels.  Requires --channel.""",
    )

def add_parser_known(p):
    p.add_argument(
        "--unknown",
        action="store_true",
        default=False,
        dest='unknown',
        help=argparse.SUPPRESS,
    )

def add_parser_use_index_cache(p):
    p.add_argument(
        "--use-index-cache",
        action="store_true",
        default=False,
        help="Use cache of channel index files.",
    )


def add_parser_no_use_index_cache(p):
    p.add_argument(
        "--no-use-index-cache",
        action="store_false",
        default=True,
        dest="use_index_cache",
        help="Force fetching of channel index files.",
    )

def add_parser_copy(p):
    p.add_argument(
        '--copy',
        action="store_true",
        help="Install all packages using copies instead of hard- or soft-linking."
        )

def add_parser_pscheck(p):
    p.add_argument(
        "--force-pscheck",
        action="store_true",
        help=("No-op. Included for backwards compatibility (deprecated)."
              if config.platform == 'win' else argparse.SUPPRESS)
    )

def add_parser_install(p):
    add_parser_yes(p)
    p.add_argument(
        '-f', "--force",
        action="store_true",
        help="Force install (even when package already installed), "
               "implies --no-deps.",
    )
    add_parser_pscheck(p)
    # Add the file kwarg. We don't use {action="store", nargs='*'} as we don't
    # want to gobble up all arguments after --file.
    p.add_argument(
        "--file",
        default=[],
        action='append',
        help="Read package versions from the given file. Repeated file "
             "specifications can be passed (e.g. --file=file1 --file=file2).",
    )
    add_parser_known(p)
    p.add_argument(
        "--no-deps",
        action="store_true",
        help="Do not install dependencies.",
    )
    p.add_argument(
        '-m', "--mkdir",
        action="store_true",
        help="Create the environment directory if necessary.",
    )
    add_parser_use_index_cache(p)
    add_parser_use_local(p)
    add_parser_offline(p)
    add_parser_no_pin(p)
    add_parser_channels(p)
    add_parser_prefix(p)
    add_parser_quiet(p)
    add_parser_copy(p)
    p.add_argument(
        "--alt-hint",
        action="store_true",
        default=False,
        help="Use an alternate algorithm to generate an unsatisfiability hint.")
    p.add_argument(
        "--update-dependencies", "--update-deps",
        action="store_true",
        dest="update_deps",
        default=config.update_dependencies,
        help="Update dependencies (default: %(default)s).",
    )
    p.add_argument(
        "--no-update-dependencies", "--no-update-deps",
        action="store_false",
        dest="update_deps",
        default=not config.update_dependencies,
        help="Don't update dependencies (default: %(default)s).",
    )
    p.add_argument(
        "--channel-priority", "--channel-pri", "--chan-pri",
        action="store_true",
        dest="channel_priority",
        default=config.channel_priority,
        help="Channel priority takes precedence over packaage version (default: %(defaults)). "
             "Note: This feature is in beta and may change in a future release."
    )
    p.add_argument(
        "--no-channel-priority", "--no-channel-pri", "--no-chan-pri",
        action="store_true",
        dest="channel_priority",
        default=not config.channel_priority,
        help="Package version takes precedence over channel priority (default: %(defaults)). "
             "Note: This feature is in beta and may change in a future release."
    )
    add_parser_show_channel_urls(p)

    if 'update' in p.prog:
        # I don't know if p.prog is the correct thing to use here but it's the
        # only thing that seemed to contain the command name
        p.add_argument(
            'packages',
            metavar='package_spec',
            action="store",
            nargs='*',
            help="Packages to update in the conda environment.",
        ).completer = InstalledPackages
    else:  # create or install
        # Same as above except the completer is not only installed packages
        p.add_argument(
            'packages',
            metavar='package_spec',
            action="store",
            nargs='*',
            help="Packages to install into the conda environment.",
        ).completer = Packages

def add_parser_use_local(p):
    p.add_argument(
        "--use-local",
        action="store_true",
        default=False,
        help="Use locally built packages.",
    )

def add_parser_offline(p):
    p.add_argument(
        "--offline",
        action="store_true",
        default=False,
        help="Offline mode, don't connect to the Internet.",
    )


def add_parser_no_pin(p):
    p.add_argument(
        "--no-pin",
        action="store_false",
        default=True,
        dest='pinned',
        help="Ignore pinned file.",
    )

def add_parser_show_channel_urls(p):
    p.add_argument(
        "--show-channel-urls",
        action="store_true",
        dest="show_channel_urls",
        default=config.show_channel_urls,
        help="Show channel urls (default: %(default)s).",
    )
    p.add_argument(
        "--no-show-channel-urls",
        action="store_false",
        dest="show_channel_urls",
        help="Don't show channel urls.",
    )

def ensure_use_local(args):
    if not args.use_local:
        return
    try:
        from conda_build.config import croot  # noqa
    except ImportError:
        error_and_exit("you need to have 'conda-build >= 1.7.1' installed"
                       " to use the --use-local option",
                       json=args.json, error_type="RuntimeError")

def ensure_override_channels_requires_channel(args, dashc=True):
    if args.override_channels and not (args.channel or args.use_local):
        if dashc:
            error_and_exit('--override-channels requires -c/--channel or --use-local',
                           json=args.json, error_type="ValueError")
        else:
            error_and_exit('--override-channels requires --channel or --use-local',
                           json=args.json, error_type="ValueError")

def confirm(args, message="Proceed", choices=('yes', 'no'), default='yes'):
    assert default in choices, default
    if args.dry_run:
        print("Dry run: exiting")
        sys.exit(0)

    options = []
    for option in choices:
        if option == default:
            options.append('[%s]' % option[0])
        else:
            options.append(option[0])
    message = "%s (%s)? " % (message, '/'.join(options))
    choices = {alt: choice
               for choice in choices
               for alt in [choice, choice[0]]}
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
    if args.dry_run:
        print("Dry run: exiting")
        sys.exit(0)
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
        error_and_exit('either -n NAME or -p PREFIX option required,\n'
                       '       try "conda %s -h" for more details' % command,
                       json=getattr(args, 'json', False),
                       error_type="ValueError")

def find_prefix_name(name):
    if name == config.root_env_name:
        return config.root_dir
    # always search cwd in addition to envs dirs (for relative path access)
    envs_dirs = config.envs_dirs + [os.getcwd(), ]
    for envs_dir in envs_dirs:
        prefix = join(envs_dir, name)
        if isdir(prefix):
            return prefix
    return None

def get_prefix(args, search=True):
    if args.name:
        if '/' in args.name:
            error_and_exit("'/' not allowed in environment name: %s" %
                           args.name,
                           json=getattr(args, 'json', False),
                           error_type="ValueError")
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

def check_write(command, prefix, json=False):
    if inroot_notwritable(prefix):
        from conda.cli.help import root_read_only

        root_read_only(command, prefix, json=json)

# -------------------------------------------------------------------------

def arg2spec(arg, json=False, update=False):
    try:
        spec = MatchSpec(spec_from_line(arg))
    except:
        error_and_exit('invalid package specification: %s' % arg,
                       json=json, error_type="ValueError")
    name = spec.name
    if name in config.disallow:
        error_and_exit("specification '%s' is disallowed" % name,
                       json=json,
                       error_type="ValueError")
    if spec.strictness > 1 and update:
        error_and_exit("""version specifications not allowed with 'update'; use
    conda update  %s%s  or
    conda install %s""" % (name, ' ' * (len(arg)-len(name)), arg),
                       json=json, error_type="ValueError")
    if spec.strictness != 2:
        return str(spec)
    ver = spec.vspecs.spec
    if isinstance(ver, tuple) or ver.startswith(('=', '>', '<', '!')) or ver.endswith('*'):
        return str(spec)
    elif ver.endswith('.0'):
        return '%s %s|%s*' % (name, ver[:-2], ver)
    else:
        return '%s %s*' % (name, ver)


def specs_from_args(args, json=False):
    return [arg2spec(arg, json=json) for arg in args]


spec_pat = re.compile(r'''
(?P<name>[^=<>!\s]+)               # package name
\s*                                # ignore spaces
(
  (?P<cc>=[^=<>!]+(=[^=<>!]+)?)    # conda constraint
  |
  (?P<pc>[=<>!]{1,2}.+)            # new (pip-style) constraint(s)
)?
$                                  # end-of-line
''', re.VERBOSE)

def strip_comment(line):
    return line.split('#')[0].rstrip()

def spec_from_line(line):
    m = spec_pat.match(strip_comment(line))
    if m is None:
        return None
    name, cc, pc = (m.group('name').lower(), m.group('cc'), m.group('pc'))
    if cc:
        return name + cc.replace('=', ' ')
    elif pc:
        return name + ' ' + pc.replace(' ', '')
    else:
        return name


def specs_from_url(url, json=False):
    from conda.fetch import TmpDownload

    explicit = False
    with TmpDownload(url, verbose=False) as path:
        specs = []
        try:
            for line in open(path):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line == '@EXPLICIT':
                    explicit = True
                if explicit:
                    specs.append(line)
                    continue
                spec = spec_from_line(line)
                if spec is None:
                    error_and_exit("could not parse '%s' in: %s" % (line, url),
                                   json=json,
                                   error_type="ValueError")
                specs.append(spec)
        except IOError:
            error_and_exit('cannot open file: %s' % path,
                           json=json,
                           error_type="IOError")
    return specs


def names_in_specs(names, specs):
    return any(spec.split()[0] in names for spec in specs)


def check_specs(prefix, specs, json=False, create=False):
    if len(specs) == 0:
        msg = ('too few arguments, must supply command line '
               'package specs or --file')
        if create:
            msg += textwrap.dedent("""

                You can specify one or more default packages to install when creating
                an environment.  Doing so allows you to call conda create without
                explicitly providing any package names.

                To set the provided packages, call conda config like this:

                    conda config --add create_default_packages PACKAGE_NAME
            """)
        error_and_exit(msg, json=json, error_type="ValueError")


def disp_features(features):
    if features:
        return '[%s]' % ' '.join(features)
    else:
        return ''


def stdout_json(d):
    import json

    json.dump(d, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write('\n')


def error_and_exit(message, json=False, newline=False, error_text=True,
                   error_type=None):
    if json:
        stdout_json(dict(error=message, error_type=error_type))
        sys.exit(1)
    else:
        if newline:
            print()

        if error_text:
            sys.exit("Error: " + message)
        else:
            sys.exit(message)


def exception_and_exit(exc, **kwargs):
    if 'error_type' not in kwargs:
        kwargs['error_type'] = exc.__class__.__name__
    error_and_exit('; '.join(map(str, exc.args)), **kwargs)


def get_index_trap(*args, **kwargs):
    """
    Retrieves the package index, but traps exceptions and reports them as
    JSON if necessary.
    """
    from conda.api import get_index

    if 'json' in kwargs:
        json = kwargs['json']
        del kwargs['json']
    else:
        json = False

    try:
        return get_index(*args, **kwargs)
    except BaseException as e:
        if json:
            exception_and_exit(e, json=json)
        else:
            raise


@contextlib.contextmanager
def json_progress_bars(json=False):
    if json:
        with console.json_progress_bars():
            yield
    else:
        yield


def stdout_json_success(success=True, **kwargs):
    result = {'success': success}
    result.update(kwargs)
    stdout_json(result)

root_no_rm = 'python', 'pycosat', 'pyyaml', 'conda', 'openssl', 'requests'


def handle_envs_list(acc, output=True):
    from conda import misc

    if output:
        print("# conda environments:")
        print("#")

    def disp_env(prefix):
        fmt = '%-20s  %s  %s'
        default = '*' if prefix == config.default_prefix else ' '
        name = (config.root_env_name if prefix == config.root_dir else
                basename(prefix))
        if output:
            print(fmt % (name, default, prefix))

    for prefix in misc.list_prefixes():
        disp_env(prefix)
        if prefix != config.root_dir:
            acc.append(prefix)

    if output:
        print()
