from __future__ import print_function, division, absolute_import

import argparse
import contextlib
import os
import re
import sys
import textwrap
from os.path import abspath, basename, expanduser, isdir, join

from .. import console
from ..config import (envs_dirs, default_prefix, platform, update_dependencies,
                      channel_priority, show_channel_urls, always_yes, root_env_name,
                      root_dir, root_writable, disallow, set_offline, is_offline)
from ..exceptions import (DryRunExit, CondaSystemExit, CondaRuntimeError,
                          CondaValueError, CondaFileIOError, TooFewArgumentsError)
from ..install import dist2quad
from ..resolve import MatchSpec
from ..utils import memoize


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
        for dir in envs_dirs:
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
        from ..api import get_index
        args = self.parsed_args
        call_dict = dict(channel_urls=args.channel or (),
                         use_cache=True,
                         prepend=not args.override_channels,
                         unknown=args.unknown)
        if hasattr(args, 'platform'):  # in search
            call_dict['platform'] = args.platform
        index = get_index(**call_dict)
        return [dist2quad(i)[0] for i in index]

class InstalledPackages(Completer):
    def __init__(self, prefix, parsed_args, **kwargs):
        self.prefix = prefix
        self.parsed_args = parsed_args

    @memoize
    def _get_items(self):
        import conda.install
        packages = conda.install.linked(get_prefix(self.parsed_args))
        return [dist2quad(i)[0] for i in packages]

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
        help="Name of environment (in %s)." % os.pathsep.join(envs_dirs),
        metavar="ENVIRONMENT",
        choices=Environments(),
    )
    npgroup.add_argument(
        '-p', "--prefix",
        action="store",
        help="Full path to environment prefix (default: %s)." % default_prefix,
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
              if platform == 'win' else argparse.SUPPRESS)
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
        default=update_dependencies,
        help="Update dependencies (default: %(default)s).",
    )
    p.add_argument(
        "--no-update-dependencies", "--no-update-deps",
        action="store_false",
        dest="update_deps",
        default=not update_dependencies,
        help="Don't update dependencies (default: %(default)s).",
    )
    p.add_argument(
        "--channel-priority", "--channel-pri", "--chan-pri",
        action="store_true",
        dest="channel_priority",
        default=channel_priority,
        help="Channel priority takes precedence over package version (default: %(default)s). "
             "Note: This feature is in beta and may change in a future release."
    )
    p.add_argument(
        "--no-channel-priority", "--no-channel-pri", "--no-chan-pri",
        action="store_true",
        dest="channel_priority",
        default=not channel_priority,
        help="Package version takes precedence over channel priority (default: %(default)s). "
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

class OfflineAction(argparse.Action):
    def __call__(self, *args, **kwargs):
        set_offline()

def add_parser_offline(p):
    p.add_argument(
        "--offline",
        action=OfflineAction,
        default=is_offline(),
        help="Offline mode, don't connect to the Internet.",
        nargs=0
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
        default=show_channel_urls,
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
    except ImportError as e:
        raise CondaRuntimeError("you need to have 'conda-build >= 1.7.1' installed"
                                " to use the --use-local option", args.json, e)

def ensure_override_channels_requires_channel(args, dashc=True):
    if args.override_channels and not (args.channel or args.use_local):
        if dashc:
            raise CondaValueError('--override-channels requires -c/--channel'
                                  ' or --use-local', args.json)
        else:
            raise CondaValueError('--override-channels requires --channel'
                                  'or --use-local', args.json)

def confirm(args, message="Proceed", choices=('yes', 'no'), default='yes'):
    assert default in choices, default
    if args.dry_run:
        raise DryRunExit

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
        raise DryRunExit
    if args.yes or always_yes:
        return True
    try:
        choice = confirm(args, message=message, choices=('yes', 'no'),
                         default=default)
    except KeyboardInterrupt as e:
        raise CondaSystemExit("\nOperation aborted.  Exiting.", e)
    if choice == 'yes':
        return True
    if exit_no:
        raise CondaSystemExit('Exiting')
    return False

# --------------------------------------------------------------------

def ensure_name_or_prefix(args, command):
    if not (args.name or args.prefix):
        raise CondaValueError('either -n NAME or -p PREFIX option required,\n'
                              'try "conda %s -h" for more details' % command,
                              getattr(args, 'json', False))

def find_prefix_name(name):
    if name == root_env_name:
        return root_dir
    # always search cwd in addition to envs dirs (for relative path access)
    for envs_dir in envs_dirs + [os.getcwd(), ]:
        prefix = join(envs_dir, name)
        if isdir(prefix):
            return prefix
    return None

def get_prefix(args, search=True):
    if args.name:
        if '/' in args.name:
            raise CondaValueError("'/' not allowed in environment name: %s" %
                                  args.name, getattr(args, 'json', False))
        if args.name == root_env_name:
            return root_dir
        if search:
            prefix = find_prefix_name(args.name)
            if prefix:
                return prefix
        return join(envs_dirs[0], args.name)

    if args.prefix:
        return abspath(expanduser(args.prefix))

    return default_prefix

def inroot_notwritable(prefix):
    """
    return True if the prefix is under root and root is not writeable
    """
    return (abspath(prefix).startswith(root_dir) and
            not root_writable)

def name_prefix(prefix):
    if abspath(prefix) == root_dir:
        return root_env_name
    return basename(prefix)

def check_write(command, prefix, json=False):
    if inroot_notwritable(prefix):
        from .help import root_read_only

        root_read_only(command, prefix, json=json)

# -------------------------------------------------------------------------

def arg2spec(arg, json=False, update=False):
    try:
        spec = MatchSpec(spec_from_line(arg), normalize=True)
    except:
        raise CondaValueError('invalid package specification: %s' % arg, json)

    name = spec.name
    if name in disallow:
        raise CondaValueError("specification '%s' is disallowed" % name, json)

    if not spec.is_simple() and update:
        raise CondaValueError("""version specifications not allowed with 'update'; use
    conda update  %s%s  or
    conda install %s""" % (name, ' ' * (len(arg) - len(name)), arg), json)

    return str(spec)


def specs_from_args(args, json=False):
    return [arg2spec(arg, json=json) for arg in args]


spec_pat = re.compile(r'''
(?P<name>[^=<>!\s]+)               # package name
\s*                                # ignore spaces
(
  (?P<cc>=[^=]+(=[^=]+)?)          # conda constraint
  |
  (?P<pc>(?:[=!]=|[><]=?).+)       # new (pip-style) constraint(s)
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
    from ..fetch import TmpDownload

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
                    raise CondaValueError("could not parse '%s' in: %s" %
                                          (line, url), json)
                specs.append(spec)
        except IOError as e:
            raise CondaFileIOError('cannot open file: %s' % path, json, e)
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
        raise TooFewArgumentsError(msg, json)


def disp_features(features):
    if features:
        return '[%s]' % ' '.join(features)
    else:
        return ''


def stdout_json(d):
    import json

    json.dump(d, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write('\n')


def get_index_trap(*args, **kwargs):
    """
    Retrieves the package index, but traps exceptions and reports them as
    JSON if necessary.
    """
    from ..api import get_index
    kwargs.pop('json')
    return get_index(*args, **kwargs)


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
        default = '*' if prefix == default_prefix else ' '
        name = (root_env_name if prefix == root_dir else
                basename(prefix))
        if output:
            print(fmt % (name, default, prefix))

    for prefix in misc.list_prefixes():
        disp_env(prefix)
        if prefix != root_dir:
            acc.append(prefix)

    if output:
        print()
