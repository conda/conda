from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import contextlib
from functools import partial
import json
import os
from os.path import abspath, basename, isfile, join
import re
import sys

from .. import console
from .._vendor.auxlib.entity import EntityEncoder
from ..base.constants import ROOT_ENV_NAME
from ..base.context import context, get_prefix as context_get_prefix
from ..common.compat import iteritems
from ..common.constants import NULL
from ..common.path import is_private_env, prefix_to_env_name
from ..core.linked_data import linked_data
from ..exceptions import (CondaFileIOError, CondaRuntimeError, CondaSystemExit, CondaValueError,
                          DryRunExit)
from ..resolve import MatchSpec
from ..utils import memoize


get_prefix = partial(context_get_prefix, context)


class NullCountAction(argparse._CountAction):

    @staticmethod
    def _ensure_value(namespace, name, value):
        if getattr(namespace, name, NULL) in (NULL, None):
            setattr(namespace, name, value)
        return getattr(namespace, name)

    def __call__(self, parser, namespace, values, option_string=None):
        new_count = self._ensure_value(namespace, self.dest, 0) + 1
        setattr(namespace, self.dest, new_count)


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
        for dir in context.envs_dirs:
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
        from conda.core.index import get_index
        args = self.parsed_args
        call_dict = dict(channel_urls=args.channel or (),
                         use_cache=True,
                         prepend=not args.override_channels,
                         unknown=args.unknown)
        if hasattr(args, 'platform'):  # in search
            call_dict['platform'] = args.platform
        index = get_index(**call_dict)
        return [record.name for record in index]

class InstalledPackages(Completer):
    def __init__(self, prefix, parsed_args, **kwargs):
        self.prefix = prefix
        self.parsed_args = parsed_args

    @memoize
    def _get_items(self):
        from conda.core.linked_data import linked
        packages = linked(context.prefix_w_legacy_search)
        return [dist.quad[0] for dist in packages]

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
        help="Name of environment (in %s)." % os.pathsep.join(context.envs_dirs),
        metavar="ENVIRONMENT",
        choices=Environments(),
    )
    npgroup.add_argument(
        '-p', "--prefix",
        action="store",
        help="Full path to environment prefix (default: %s)." % context.default_prefix,
        metavar='PATH',
    )


def add_parser_yes(p):
    p.add_argument(
        "-y", "--yes",
        action="store_true",
        default=NULL,
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
        default=NULL,
        help="Report all output as json. Suitable for using conda programmatically."
    )
    p.add_argument(
        "--debug",
        action="store_true",
        default=NULL,
        help="Show debug output.",
    )
    p.add_argument(
        "--verbose", "-v",
        action=NullCountAction,
        help="Use once for info, twice for debug, three times for trace.",
        dest="verbosity",
        default=NULL,
    )


def add_parser_quiet(p):
    p.add_argument(
        '-q', "--quiet",
        action="store_true",
        default=NULL,
        help="Do not display progress bar.",
    )

def add_parser_channels(p):
    p.add_argument(
        '-c', '--channel',
        dest='channel',  # apparently conda-build uses this; someday rename to channels are remove context.channels alias to channel  # NOQA
        # TODO: if you ever change 'channel' to 'channels', make sure you modify the context.channels property accordingly # NOQA
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
        default=NULL,
        help="Install all packages using copies instead of hard- or soft-linking."
    )

def add_parser_pscheck(p):
    p.add_argument(
        "--force-pscheck",
        action="store_true",
        help=("No-op. Included for backwards compatibility (deprecated)."
              if context.platform == 'win' else argparse.SUPPRESS)
    )

def add_parser_install(p):
    add_parser_yes(p)
    p.add_argument(
        '-f', "--force",
        action="store_true",
        default=NULL,
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
        default=NULL,
        help="Update dependencies (default: %s)." % context.update_dependencies,
    )
    p.add_argument(
        "--no-update-dependencies", "--no-update-deps",
        action="store_false",
        dest="update_deps",
        default=NULL,
        help="Don't update dependencies (default: %s)." % (not context.update_dependencies,),
    )
    p.add_argument(
        "--channel-priority", "--channel-pri", "--chan-pri",
        action="store_true",
        dest="channel_priority",
        default=NULL,
        help="Channel priority takes precedence over package version (default: %s). "
             "Note: This feature is in beta and may change in a future release."
             "" % (context.channel_priority,)
    )
    p.add_argument(
        "--no-channel-priority", "--no-channel-pri", "--no-chan-pri",
        action="store_false",
        dest="channel_priority",
        default=NULL,
        help="Package version takes precedence over channel priority (default: %s). "
             "Note: This feature is in beta and may change in a future release."
             "" % (not context.channel_priority,)
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
        action='store_true',
        default=NULL,
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
        default=NULL,
        help="Show channel urls (default: %s)." % context.show_channel_urls,
    )
    p.add_argument(
        "--no-show-channel-urls",
        action="store_false",
        dest="show_channel_urls",
        help="Don't show channel urls.",
    )


def add_parser_create_install_update(p):
    p.add_argument(
        "--clobber",
        action="store_true",
        default=NULL,
        help="Allow clobbering of overlapping file paths within packages, "
             "and suppress related warnings.",
    )


def ensure_use_local(args):
    if not args.use_local:
        return
    try:
        from conda_build.config import croot  # noqa
    except ImportError as e:
        raise CondaRuntimeError("%s: you need to have 'conda-build >= 1.7.1' installed"
                                " to use the --use-local option." % e)

def ensure_override_channels_requires_channel(args, dashc=True):
    if args.override_channels and not (args.channel or args.use_local):
        if dashc:
            raise CondaValueError('--override-channels requires -c/--channel'
                                  ' or --use-local')
        else:
            raise CondaValueError('--override-channels requires --channel'
                                  'or --use-local')

def confirm(args, message="Proceed", choices=('yes', 'no'), default='yes'):
    assert default in choices, default
    if args.dry_run:
        raise DryRunExit()

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
        raise DryRunExit()
    if context.always_yes:
        return True
    try:
        choice = confirm(args, message=message, choices=('yes', 'no'),
                         default=default)
    except KeyboardInterrupt as e:
        raise CondaSystemExit("\nOperation aborted.  Exiting.", e)
    if choice == 'yes':
        return True
    if exit_no:
        raise SystemExit('Exiting\n')
    return False

# --------------------------------------------------------------------


def ensure_name_or_prefix(args, command):
    if not (args.name or args.prefix):
        raise CondaValueError('either -n NAME or -p PREFIX option required,\n'
                              'try "conda %s -h" for more details' % command)


def name_prefix(prefix):
    if abspath(prefix) == context.root_prefix:
        return ROOT_ENV_NAME
    return basename(prefix)


# -------------------------------------------------------------------------

def arg2spec(arg, json=False, update=False):
    try:
        spec = MatchSpec(spec_from_line(arg), normalize=True)
    except:
        raise CondaValueError('invalid package specification: %s' % arg)

    name = spec.name
    if name in context.disallow:
        raise CondaValueError("specification '%s' is disallowed" % name)

    if not spec.is_simple() and update:
        raise CondaValueError("""version specifications not allowed with 'update'; use
    conda update  %s%s  or
    conda install %s""" % (name, ' ' * (len(arg) - len(name)), arg))

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
                                          (line, url))
                specs.append(spec)
        except IOError as e:
            raise CondaFileIOError(path, e)
    return specs


def names_in_specs(names, specs):
    return any(spec.split()[0] in names for spec in specs)


def disp_features(features):
    if features:
        return '[%s]' % ' '.join(features)
    else:
        return ''


def stdout_json(d):
    import json

    json.dump(d, sys.stdout, indent=2, sort_keys=True, cls=EntityEncoder)
    sys.stdout.write('\n')


def get_index_trap(*args, **kwargs):
    """
    Retrieves the package index, but traps exceptions and reports them as
    JSON if necessary.
    """
    from conda.core.index import get_index
    kwargs.pop('json', None)
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

    # this code reverts json output for plan back to previous behavior
    #   relied on by Anaconda Navigator and nb_conda
    actions = kwargs.get('actions', {})
    if 'LINK' in actions:
        actions['LINK'] = [str(d) for d in actions['LINK']]
    if 'UNLINK' in actions:
        actions['UNLINK'] = [str(d) for d in actions['UNLINK']]

    result.update(kwargs)
    stdout_json(result)


def handle_envs_list(acc, output=True):
    from conda import misc

    if output:
        print("# conda environments:")
        print("#")

    def disp_env(prefix):
        fmt = '%-20s  %s  %s'
        default = '*' if prefix == context.default_prefix else ' '
        name = (ROOT_ENV_NAME if prefix == context.root_prefix else
                basename(prefix))
        if output:
            print(fmt % (name, default, prefix))

    for prefix in misc.list_prefixes():
        disp_env(prefix)
        if prefix != context.root_prefix:
            acc.append(prefix)

    if output:
        print()


def get_private_envs_json():
    path_to_private_envs = join(context.root_prefix, "conda-meta", "private_envs")
    if not isfile(path_to_private_envs):
        return None
    try:
        with open(path_to_private_envs, "r") as f:
            private_envs_json = json.load(f)
    except json.decoder.JSONDecodeError:
        private_envs_json = {}
    return private_envs_json


def prefix_if_in_private_env(spec):
    private_envs_json = get_private_envs_json()
    if not private_envs_json:
        return None
    prefixes = tuple(prefix for pkg, prefix in iteritems(private_envs_json) if
                     pkg.startswith(spec))
    prefix = prefixes[0] if len(prefixes) > 0 else None
    return prefix


def pkg_if_in_private_env(spec):
    private_envs_json = get_private_envs_json()
    pkgs = tuple(pkg for pkg, prefix in iteritems(private_envs_json) if pkg.startswith(spec))
    pkg = pkgs[0] if len(pkgs) > 0 else None
    return pkg


def create_prefix_spec_map_with_deps(r, specs, default_prefix):
    prefix_spec_map = {}
    for spec in specs:
        spec_prefix = prefix_if_in_private_env(spec)
        spec_prefix = spec_prefix if spec_prefix is not None else default_prefix
        if spec_prefix in prefix_spec_map.keys():
            prefix_spec_map[spec_prefix].add(spec)
        else:
            prefix_spec_map[spec_prefix] = {spec}

        if is_private_env(prefix_to_env_name(spec_prefix, context.root_prefix)):
            linked = linked_data(spec_prefix)
            for linked_spec in linked:
                if not linked_spec.name.startswith(spec) and r.depends_on(spec, linked_spec):
                    prefix_spec_map[spec_prefix].add(linked_spec.name)
    return prefix_spec_map
