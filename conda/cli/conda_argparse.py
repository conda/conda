# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from argparse import (ArgumentParser as ArgumentParserBase, RawDescriptionHelpFormatter, SUPPRESS,
                      _CountAction, _HelpAction)
from logging import getLogger
import os
from os.path import abspath, expanduser, join
from subprocess import Popen
import sys
from textwrap import dedent

from .. import __version__
from ..base.constants import CONDA_HOMEPAGE_URL
from ..common.constants import NULL

log = getLogger(__name__)

# duplicated code in the interest of import efficiency
on_win = bool(sys.platform == "win32")
user_rc_path = abspath(expanduser('~/.condarc'))
escaped_user_rc_path = user_rc_path.replace("%", "%%")
escaped_sys_rc_path = abspath(join(sys.prefix, '.condarc')).replace("%", "%%")


def generate_parser():
    p = ArgumentParser(
        description='conda is a tool for managing and deploying applications,'
                    ' environments and packages.',
    )
    p.add_argument(
        '-V', '--version',
        action='version',
        version='conda %s' % __version__,
        help="Show the conda version number and exit."
    )
    p.add_argument(
        "--debug",
        action="store_true",
        help=SUPPRESS,
    )
    p.add_argument(
        "--json",
        action="store_true",
        help=SUPPRESS,
    )
    sub_parsers = p.add_subparsers(
        metavar='command',
        dest='cmd',
    )
    # http://bugs.python.org/issue9253
    # http://stackoverflow.com/a/18283730/1599393
    sub_parsers.required = True

    configure_parser_clean(sub_parsers)
    configure_parser_config(sub_parsers)
    configure_parser_create(sub_parsers)
    configure_parser_help(sub_parsers)
    configure_parser_info(sub_parsers)
    configure_parser_install(sub_parsers)
    configure_parser_list(sub_parsers)
    configure_parser_package(sub_parsers)
    configure_parser_remove(sub_parsers)
    configure_parser_remove(sub_parsers, name='uninstall')
    configure_parser_search(sub_parsers)
    configure_parser_update(sub_parsers)
    configure_parser_update(sub_parsers, name='upgrade')

    return p


def do_call(args, parser):
    relative_mod, func_name = args.func.rsplit('.', 1)
    # func_name should always be 'execute'
    from importlib import import_module
    module = import_module(relative_mod, __name__.rsplit('.', 1)[0])
    exit_code = getattr(module, func_name)(args, parser)
    return exit_code


class ArgumentParser(ArgumentParserBase):
    def __init__(self, *args, **kwargs):
        if not kwargs.get('formatter_class'):
            kwargs['formatter_class'] = RawDescriptionHelpFormatter
        if 'add_help' not in kwargs:
            add_custom_help = True
            kwargs['add_help'] = False
        else:
            add_custom_help = False
        super(ArgumentParser, self).__init__(*args, **kwargs)

        if add_custom_help:
            add_parser_help(self)

        if self.description:
            self.description += "\n\nOptions:\n"

    def _get_action_from_name(self, name):
        """Given a name, get the Action instance registered with this parser.
        If only it were made available in the ArgumentError object. It is
        passed as it's first arg...
        """
        container = self._actions
        if name is None:
            return None
        for action in container:
            if '/'.join(action.option_strings) == name:
                return action
            elif action.metavar == name:
                return action
            elif action.dest == name:
                return action

    def error(self, message):
        import re
        from .find_commands import find_executable
        exc = sys.exc_info()[1]
        if exc:
            # this is incredibly lame, but argparse stupidly does not expose
            # reasonable hooks for customizing error handling
            if hasattr(exc, 'argument_name'):
                argument = self._get_action_from_name(exc.argument_name)
            else:
                argument = None
            if argument and argument.dest == "cmd":
                m = re.match(r"invalid choice: u?'([\w\-]*?)'", exc.message)
                if m:
                    cmd = m.group(1)
                    if not cmd:
                        self.print_help()
                        sys.exit(0)
                    else:
                        executable = find_executable('conda-' + cmd)
                        if not executable:
                            from ..exceptions import CommandNotFoundError
                            raise CommandNotFoundError(cmd)
                        args = [find_executable('conda-' + cmd)]
                        args.extend(sys.argv[2:])
                        p = Popen(args)
                        try:
                            p.communicate()
                        except KeyboardInterrupt:
                            p.wait()
                        finally:
                            sys.exit(p.returncode)

        super(ArgumentParser, self).error(message)

    def print_help(self):
        super(ArgumentParser, self).print_help()

        if sys.argv[1:] in ([], [''], ['help'], ['-h'], ['--help']):
            from .find_commands import find_commands
            other_commands = find_commands()
            if other_commands:
                builder = ['']
                builder.append("conda commands available from other packages:")
                builder.extend('  %s' % cmd for cmd in sorted(other_commands))
                print('\n'.join(builder))


class NullCountAction(_CountAction):

    @staticmethod
    def _ensure_value(namespace, name, value):
        if getattr(namespace, name, NULL) in (NULL, None):
            setattr(namespace, name, value)
        return getattr(namespace, name)

    def __call__(self, parser, namespace, values, option_string=None):
        new_count = self._ensure_value(namespace, self.dest, 0) + 1
        setattr(namespace, self.dest, new_count)


# #############################################################################################
#
# sub-parsers
#
# #############################################################################################

def configure_parser_clean(sub_parsers):
    descr = dedent("""
    Remove unused packages and caches.
    """)
    example = dedent("""
    Examples:

        conda clean --tarballs
    """)
    p = sub_parsers.add_parser(
        'clean',
        description=descr,
        help=descr,
        epilog=example,
    )
    add_parser_yes(p)
    add_parser_json(p)
    add_parser_quiet(p)
    p.add_argument(
        "-a", "--all",
        action="store_true",
        help="Remove index cache, lock files, tarballs, "
             "unused cache packages, and source cache.",
    )
    p.add_argument(
        "-i", "--index-cache",
        action="store_true",
        help="Remove index cache.",
    )
    p.add_argument(
        "-l", "--lock",
        action="store_true",
        help="Remove all conda lock files.",
    )
    p.add_argument(
        "-t", "--tarballs",
        action="store_true",
        help="Remove cached package tarballs.",
    )
    p.add_argument(
        '-p', '--packages',
        action='store_true',
        help="""Remove unused cached packages. Warning: this does not check
    for symlinked packages.""",
    )
    p.add_argument(
        '-s', '--source-cache',
        action='store_true',
        help="""Remove files from the source cache of conda build.""",
    )
    p.set_defaults(func='.main_clean.execute')


def configure_parser_info(sub_parsers):
    help = "Display information about current conda install."

    example = dedent("""

    Examples:

        conda info -a
    """)
    p = sub_parsers.add_parser(
        'info',
        description=help,
        help=help,
        epilog=example,
    )
    add_parser_json(p)
    add_parser_offline(p)
    p.add_argument(
        '-a', "--all",
        action="store_true",
        help="Show all information, (environments, license, and system "
             "information.")
    p.add_argument(
        '-e', "--envs",
        action="store_true",
        help="List all known conda environments.",
    )
    p.add_argument(
        '-l', "--license",
        action="store_true",
        help="Display information about the local conda licenses list.",
    )
    p.add_argument(
        '-s', "--system",
        action="store_true",
        help="List environment variables.",
    )
    p.add_argument(
        'packages',
        action="store",
        nargs='*',
        help="Display information about packages.",
    )
    p.add_argument(
        '--base',
        action='store_true',
        help='Display base environment path.',
    )
    p.add_argument(
        '--root',
        action='store_true',
        help=SUPPRESS,
        dest='base',
    )
    p.add_argument(
        '--unsafe-channels',
        action='store_true',
        help='Display list of channels with tokens exposed.',
    )
    p.set_defaults(func='.main_info.execute')


def configure_parser_config(sub_parsers):
    descr = dedent("""
    Modify configuration values in .condarc.  This is modeled after the git
    config command.  Writes to the user .condarc file (%s) by default.

    """) % escaped_user_rc_path

    # Note, the extra whitespace in the list keys is on purpose. It's so the
    # formatting from help2man is still valid YAML (otherwise it line wraps the
    # keys like "- conda - defaults"). Technically the parser here still won't
    # recognize it because it removes the indentation, but at least it will be
    # valid.
    additional_descr = """
    See `conda config --describe` or %s/docs/config.html
    for details on all the options that can go in .condarc.

    Examples:

    Display all configuration values as calculated and compiled:

        conda config --show

    Display all identified configuration sources:

        conda config --show-sources

    Describe all available configuration options:

        conda config --describe

    Add the conda-canary channel:

        conda config --add channels conda-canary

    Set the output verbosity to level 3 (highest):

        conda config --set verbosity 3

    Get the channels defined in the system .condarc:

        conda config --get channels --system

    Add the 'foo' Binstar channel:

        conda config --add channels foo

    Disable the 'show_channel_urls' option:

        conda config --set show_channel_urls no
    """ % CONDA_HOMEPAGE_URL

    p = sub_parsers.add_parser(
        'config',
        description=descr,
        help=descr,
        epilog=additional_descr,
    )
    add_parser_json(p)

    # TODO: use argparse.FileType
    location = p.add_mutually_exclusive_group()
    location.add_argument(
        "--system",
        action="store_true",
        help="""Write to the system .condarc file ({system}). Otherwise writes to the user
        config file ({user}).""".format(system=escaped_sys_rc_path,
                                        user=escaped_user_rc_path),
    )
    location.add_argument(
        "--env",
        action="store_true",
        help="Write to the active conda environment .condarc file (%s). "
             "If no environment is active, write to the user config file (%s)."
             "" % (
                 os.getenv('CONDA_PREFIX', "<no active environment>").replace("%", "%%"),
                 escaped_user_rc_path,
             ),
    )
    location.add_argument(
        "--file",
        action="store",
        help="""Write to the given file. Otherwise writes to the user config file ({user})
or the file path given by the 'CONDARC' environment variable, if it is set
(default: %(default)s).""".format(user=escaped_user_rc_path),
        default=os.environ.get('CONDARC', user_rc_path)
    )

    # XXX: Does this really have to be mutually exclusive. I think the below
    # code will work even if it is a regular group (although combination of
    # --add and --remove with the same keys will not be well-defined).
    action = p.add_mutually_exclusive_group(required=True)
    action.add_argument(
        "--show",
        nargs='*',
        default=None,
        help="Display configuration values as calculated and compiled. "
             "If no arguments given, show information for all configuration values.",
    )
    action.add_argument(
        "--show-sources",
        action="store_true",
        help="Display all identified configuration sources.",
    )
    action.add_argument(
        "--validate",
        action="store_true",
        help="Validate all configuration sources.",
    )
    action.add_argument(
        "--describe",
        nargs='*',
        default=None,
        help="Describe given configuration parameters. If no arguments given, show "
             "information for all configuration parameters.",
    )
    action.add_argument(
        "--write-default",
        action="store_true",
        help="Write the default configuration to a file. "
             "Equivalent to `conda config --describe > ~/.condarc` "
             "when no --env, --system, or --file flags are given.",
    )
    action.add_argument(
        "--get",
        nargs='*',
        action="store",
        help="Get a configuration value.",
        default=None,
        metavar='KEY',
    )
    action.add_argument(
        "--append",
        nargs=2,
        action="append",
        help="""Add one configuration value to the end of a list key.""",
        default=[],
        metavar=('KEY', 'VALUE'),
    )
    action.add_argument(
        "--prepend", "--add",
        nargs=2,
        action="append",
        help="""Add one configuration value to the beginning of a list key.""",
        default=[],
        metavar=('KEY', 'VALUE'),
    )
    action.add_argument(
        "--set",
        nargs=2,
        action="append",
        help="""Set a boolean or string key""",
        default=[],
        metavar=('KEY', 'VALUE'),
    )
    action.add_argument(
        "--remove",
        nargs=2,
        action="append",
        help="""Remove a configuration value from a list key. This removes
    all instances of the value.""",
        default=[],
        metavar=('KEY', 'VALUE'),
    )
    action.add_argument(
        "--remove-key",
        nargs=1,
        action="append",
        help="""Remove a configuration key (and all its values).""",
        default=[],
        metavar="KEY",
    )
    action.add_argument(
        "--stdin",
        action="store_true",
        help="Apply configuration information given in yaml format piped through stdin.",
    )

    p.add_argument(
        "-f", "--force",
        action="store_true",
        default=NULL,
        help=SUPPRESS,  # TODO: No longer used.  Remove in a future release.
    )

    p.set_defaults(func='.main_config.execute')


def configure_parser_create(sub_parsers):
    help = "Create a new conda environment from a list of specified packages. "
    descr = (help +
             "To use the created environment, use 'source activate "
             "envname' look in that directory first.  This command requires either "
             "the -n NAME or -p PREFIX option.")

    example = dedent("""
    Examples:

        conda create -n myenv sqlite

    """)
    p = sub_parsers.add_parser(
        'create',
        description=descr,
        help=help,
        epilog=example,
    )
    if on_win:
        p.add_argument(
            "--shortcuts",
            action="store_true",
            help="Install start menu shortcuts",
            dest="shortcuts",
            default=NULL,
        )
        p.add_argument(
            "--no-shortcuts",
            action="store_false",
            help="Don't install start menu shortcuts",
            dest="shortcuts",
            default=NULL,
        )
    add_parser_create_install_update(p)
    add_parser_json(p)
    p.add_argument(
        "--clone",
        action="store",
        help='Path to (or name of) existing local environment.',
        metavar='ENV',
    )
    p.add_argument(
        "--no-default-packages",
        action="store_true",
        help='Ignore create_default_packages in the .condarc file.',
    )
    p.set_defaults(func='.main_create.execute')


def configure_parser_help(sub_parsers):
    descr = "Displays a list of available conda commands and their help strings."

    example = dedent("""
    Examples:

        conda help install
    """)

    p = sub_parsers.add_parser(
        'help',
        description=descr,
        help=descr,
        epilog=example,
    )
    p.add_argument(
        'command',
        metavar='COMMAND',
        action="store",
        nargs='?',
        help="Print help information for COMMAND (same as: conda COMMAND --help).",
    )
    p.set_defaults(func='.main_help.execute')


def configure_parser_install(sub_parsers):
    help = "Installs a list of packages into a specified conda environment."
    descr = dedent(help + """

    This command accepts a list of package specifications (e.g, bitarray=0.8)
    and installs a set of packages consistent with those specifications and
    compatible with the underlying environment. If full compatibility cannot
    be assured, an error is reported and the environment is not changed.

    Conda attempts to install the newest versions of the requested packages. To
    accomplish this, it may update some packages that are already installed, or
    install additional packages. To prevent existing packages from updating,
    use the --no-update-deps option. This may force conda to install older
    versions of the requested packages, and it does not prevent additional
    dependency packages from being installed.

    If you wish to skip dependency checking altogether, use the '--force'
    option. This may result in an environment with incompatible packages, so
    this option must be used with great caution.

    conda can also be called with a list of explicit conda package filenames
    (e.g. ./lxml-3.2.0-py27_0.tar.bz2). Using conda in this mode implies the
    --force option, and should likewise be used with great caution. Explicit
    filenames and package specifications cannot be mixed in a single command.
    """)
    example = dedent("""
    Examples:

        conda install -n myenv scipy

    """)
    p = sub_parsers.add_parser(
        'install',
        description=descr,
        help=help,
        epilog=example,
    )
    p.add_argument(
        "--revision",
        action="store",
        help="Revert to the specified REVISION.",
        metavar='REVISION',
    )
    if on_win:
        p.add_argument(
            "--shortcuts",
            action="store_true",
            help="Install start menu shortcuts",
            dest="shortcuts",
            default=True
        )
        p.add_argument(
            "--no-shortcuts",
            action="store_false",
            help="Don't install start menu shortcuts",
            dest="shortcuts",
            default=True
        )
    add_parser_create_install_update(p)
    add_parser_json(p)
    p.set_defaults(func='.main_install.execute')


def configure_parser_list(sub_parsers):
    descr = "List linked packages in a conda environment."

    # Note, the formatting of this is designed to work well with help2man
    examples = dedent("""
    Examples:

    List all packages in the current environment:

        conda list

    List all packages installed into the environment 'myenv':

        conda list -n myenv

    Save packages for future use:

        conda list --export > package-list.txt

    Reinstall packages from an export file:

        conda create -n myenv --file package-list.txt

    """)
    p = sub_parsers.add_parser(
        'list',
        description=descr,
        help=descr,
        formatter_class=RawDescriptionHelpFormatter,
        epilog=examples,
        add_help=False,
    )
    add_parser_help(p)
    add_parser_prefix(p)
    add_parser_json(p)
    add_parser_show_channel_urls(p)
    p.add_argument(
        '-c', "--canonical",
        action="store_true",
        help="Output canonical names of packages only. Implies --no-pip. ",
    )
    p.add_argument(
        '-f', "--full-name",
        action="store_true",
        help="Only search for full names, i.e., ^<regex>$.",
    )
    p.add_argument(
        "--explicit",
        action="store_true",
        help="List explicitly all installed conda packaged with URL "
             "(output may be used by conda create --file).",
    )
    p.add_argument(
        "--md5",
        action="store_true",
        help="Add MD5 hashsum when using --explicit",
    )
    p.add_argument(
        '-e', "--export",
        action="store_true",
        help="Output requirement string only (output may be used by "
             " conda create --file).",
    )
    p.add_argument(
        '-r', "--revisions",
        action="store_true",
        help="List the revision history and exit.",
    )
    p.add_argument(
        "--no-pip",
        action="store_false",
        default=True,
        dest="pip",
        help="Do not include pip-only installed packages.")
    p.add_argument(
        'regex',
        action="store",
        nargs="?",
        help="List only packages matching this regular expression.",
    )
    p.set_defaults(func='.main_list.execute')


def configure_parser_package(sub_parsers):
    descr = "Low-level conda package utility. (EXPERIMENTAL)"
    p = sub_parsers.add_parser(
        'package',
        description=descr,
        help=descr,
    )
    add_parser_prefix(p)
    p.add_argument(
        '-w', "--which",
        metavar="PATH",
        nargs='+',
        action="store",
        help="Given some PATH print which conda package the file came from.",
    )
    p.add_argument(
        '-r', "--reset",
        action="store_true",
        help="Remove all untracked files and exit.",
    )
    p.add_argument(
        '-u', "--untracked",
        action="store_true",
        help="Display all untracked files and exit.",
    )
    p.add_argument(
        "--pkg-name",
        action="store",
        default="unknown",
        help="Package name of the created package.",
    )
    p.add_argument(
        "--pkg-version",
        action="store",
        default="0.0",
        help="Package version of the created package.",
    )
    p.add_argument(
        "--pkg-build",
        action="store",
        default=0,
        help="Package build number of the created package.",
    )
    p.set_defaults(func='.main_package.execute')


def configure_parser_remove(sub_parsers, name='remove'):
    help = "%s a list of packages from a specified conda environment."
    descr = dedent(help + """

    This command will also remove any package that depends on any of the
    specified packages as well---unless a replacement can be found without
    that dependency. If you wish to skip this dependency checking and remove
    just the requested packages, add the '--force' option. Note however that
    this may result in a broken environment, so use this with caution.
    """)
    example = dedent("""
    Examples:

        conda %s -n myenv scipy

    """)

    uninstall_help = "Alias for conda remove.  See conda remove --help."
    if name == 'remove':
        p = sub_parsers.add_parser(
            name,
            formatter_class=RawDescriptionHelpFormatter,
            description=descr % name.capitalize(),
            help=help % name.capitalize(),
            epilog=example % name,
            add_help=False,
        )
    else:
        p = sub_parsers.add_parser(
            name,
            formatter_class=RawDescriptionHelpFormatter,
            description=uninstall_help,
            help=uninstall_help,
            epilog=example % name,
            add_help=False,
        )
    add_parser_help(p)
    add_parser_yes(p)
    add_parser_json(p)
    p.add_argument(
        "--all",
        action="store_true",
        help="%s all packages, i.e., the entire environment." % name.capitalize(),
    )

    p.add_argument(
        "--force",
        action="store_true",
        help="Forces removal of a package without removing packages that depend on it. "
             "Using this option will usually leave your environment in a broken and "
             "inconsistent state.",
    )
    add_parser_no_pin(p)
    add_parser_channels(p)
    add_parser_prefix(p)
    add_parser_quiet(p)
    # Putting this one first makes it the default
    add_parser_use_index_cache(p)
    add_parser_use_local(p)
    add_parser_offline(p)
    add_parser_pscheck(p)
    add_parser_insecure(p)
    p.add_argument(
        'package_names',
        metavar='package_name',
        action="store",
        nargs='*',
        help="Package names to %s from the environment." % name,
    )
    p.add_argument(
        "--features",
        action="store_true",
        help="%s features (instead of packages)." % name.capitalize(),
    )
    p.set_defaults(func='.main_remove.execute')


def configure_parser_search(sub_parsers):
    descr = dedent("""Search for packages and display associated information.
    The input is a MatchSpec, a query language for conda packages.
    See examples below.
    """)

    example = dedent("""
    Examples:

    Search for a specific package named 'scikit-learn':

        conda search scikit-learn

    Search for packages containing 'scikit' in the package name:

        conda search *scikit*

    Note that your shell may expand '*' before handing the command over to conda.
    Therefore it is sometimes necessary to use single or double quotes around the query.

        conda search '*scikit'
        conda search "*scikit*"

    Search for packages for 64-bit Linux (by default, packages for your current
    platform are shown):

        conda search numpy[subdir=linux-64]

    Search for a specific version of a package:

        conda search 'numpy>=1.12'

    Search for a package on a specific channel

        conda search conda-forge::numpy
        conda search 'numpy[channel=conda-forge, subdir=osx-64]'
    """)
    p = sub_parsers.add_parser(
        'search',
        description=descr,
        help=descr,
        epilog=example,
    )
    add_parser_prefix(p)
    p.add_argument(
        "--canonical",
        action="store_true",
        help=SUPPRESS,
    )
    p.add_argument(
        '-f', "--full-name",
        action="store_true",
        help=SUPPRESS,
    )
    p.add_argument(
        '-i', "--info",
        action="store_true",
        help="Provide detailed information about each package. "
             "Similar to output of 'conda info package-name'."
    )
    p.add_argument(
        "--names-only",
        action="store_true",
        help=SUPPRESS,
    )
    add_parser_known(p)
    add_parser_use_index_cache(p)
    p.add_argument(
        '-o', "--outdated",
        action="store_true",
        help=SUPPRESS,
    )
    p.add_argument(
        '--platform',
        action='store',
        dest='platform',
        help="""Search the given platform. Should be formatted like 'osx-64', 'linux-32',
        'win-64', and so on. The default is to search the current platform.""",
        default=None,
    )
    p.add_argument(
        'match_spec',
        default='*',
        nargs='?',
        help=SUPPRESS,
    )
    p.add_argument(
        "--spec",
        action="store_true",
        help=SUPPRESS,
    )
    p.add_argument(
        "--reverse-dependency",
        action="store_true",
        help="Perform a reverse dependency search. When using this flag, the --full-name "
             "flag is recommended. Use 'conda info package' to see the dependencies of a "
             "package.",
    )
    add_parser_offline(p)
    add_parser_channels(p)
    add_parser_json(p)
    add_parser_use_local(p)
    add_parser_insecure(p)
    p.add_argument(
        "--envs",
        action="store_true",
        help="Search all of the current user's environments. If run as Administrator "
             "(on Windows) or UID 0 (on unix), search all known environments on the system.",
    )
    p.set_defaults(func='.main_search.execute')


def configure_parser_update(sub_parsers, name='update'):
    help = "Updates conda packages to the latest compatible version."
    descr = dedent(help + """

    This command accepts a list of package names and updates them to the latest
    versions that are compatible with all other packages in the environment.

    Conda attempts to install the newest versions of the requested packages. To
    accomplish this, it may update some packages that are already installed, or
    install additional packages. To prevent existing packages from updating,
    use the --no-update-deps option. This may force conda to install older
    versions of the requested packages, and it does not prevent additional
    dependency packages from being installed.

    If you wish to skip dependency checking altogether, use the '--force'
    option. This may result in an environment with incompatible packages, so
    this option must be used with great caution.
    """)
    example = dedent("""
    Examples:

        conda %s -n myenv scipy

    """)

    alias_help = "Alias for conda update.  See conda update --help."
    if name == 'update':
        p = sub_parsers.add_parser(
            'update',
            description=descr,
            help=descr,
            epilog=example % name,
        )
    else:
        p = sub_parsers.add_parser(
            name,
            description=alias_help,
            help=alias_help,
            epilog=example % name,
        )
    add_parser_create_install_update(p)
    add_parser_json(p)
    p.add_argument(
        "--all",
        action="store_true",
        help="Update all installed packages in the environment.",
    )
    p.set_defaults(func='.main_update.execute')


# #############################################################################################
#
# parser helpers
#
# #############################################################################################

def add_parser_create_install_update(p):
    add_parser_yes(p)
    p.add_argument(
        '-f', "--force",
        action="store_true",
        default=NULL,
        help="Force install (even when package already installed).",
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
        help="Do not install, update, remove, or change dependencies. This WILL lead "
             "to broken environments and inconsistent behavior. Use at your own risk.",
    )
    p.add_argument(
        "--only-deps",
        action="store_true",
        help="Only install dependencies.",
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
    add_parser_insecure(p)
    p.add_argument(
        "--update-dependencies", "--update-deps",
        action="store_true",
        dest="update_deps",
        default=NULL,
        help="Update dependencies. Overrides the value given by "
             "`conda config --show update_deps`.",
    )
    p.add_argument(
        "--no-update-dependencies", "--no-update-deps",
        action="store_false",
        dest="update_deps",
        default=NULL,
        help="Don't update dependencies. Overrides the value given by "
             "`conda config --show update_deps`.",
    )
    p.add_argument(
        "--channel-priority", "--channel-pri", "--chan-pri",
        action="store_true",
        dest="channel_priority",
        default=NULL,
        help="Channel priority takes precedence over package version. "
             "Overrides the value given by `conda config --show channel_priority`."
    )
    p.add_argument(
        "--no-channel-priority", "--no-channel-pri", "--no-chan-pri",
        action="store_false",
        dest="channel_priority",
        default=NULL,
        help="Package version takes precedence over channel priority. "
             "Overrides the value given by `conda config --show channel_priority`."
    )
    p.add_argument(
        "--clobber",
        action="store_true",
        default=NULL,
        help="Allow clobbering of overlapping file paths within packages, "
             "and suppress related warnings.",
    )
    add_parser_show_channel_urls(p)

    p.add_argument(
        'packages',
        metavar='package_spec',
        action="store",
        nargs='*',
        help="Packages to install or update in the conda environment.",
    )
    p.add_argument(
        "--download-only",
        action="store_true",
        default=NULL,
        help="Solve an environment and ensure package caches are populated, but exit "
             "prior to unlinking and linking packages into the prefix.",
    )


def add_parser_pscheck(p):
    p.add_argument(
        "--force-pscheck",
        action="store_true",
        help=SUPPRESS
    )


def add_parser_use_local(p):
    p.add_argument(
        "--use-local",
        action="store_true",
        default=NULL,
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
        action="store_true",
        dest='ignore_pinned',
        default=NULL,
        help="Ignore pinned file.",
    )


def add_parser_show_channel_urls(p):
    p.add_argument(
        "--show-channel-urls",
        action="store_true",
        dest="show_channel_urls",
        default=NULL,
        help="Show channel urls. "
             "Overrides the value given by `conda config --show show_channel_urls`.",
    )
    p.add_argument(
        "--no-show-channel-urls",
        action="store_false",
        dest="show_channel_urls",
        help="Don't show channel urls. "
             "Overrides the value given by `conda config --show show_channel_urls`.",
    )


def add_parser_copy(p):
    p.add_argument(
        '--copy',
        action="store_true",
        default=NULL,
        help="Install all packages using copies instead of hard- or soft-linking."
    )


def add_parser_help(p):
    """
    So we can use consistent capitalization and periods in the help. You must
    use the add_help=False argument to ArgumentParser or add_parser to use
    this. Add this first to be consistent with the default argparse output.

    """
    p.add_argument(
        '-h', '--help',
        action=_HelpAction,
        help="Show this help message and exit.",
    )


def add_parser_prefix(p):
    npgroup = p.add_mutually_exclusive_group()
    npgroup.add_argument(
        '-n', "--name",
        action="store",
        help="Name of environment.",
        metavar="ENVIRONMENT",
    )
    npgroup.add_argument(
        '-p', "--prefix",
        action="store",
        help="Full path to environment prefix.",
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
        help=SUPPRESS,
    )


def add_parser_use_index_cache(p):
    p.add_argument(
        "-C", "--use-index-cache",
        action="store_true",
        default=False,
        help="Use cache of channel index files, even if it has expired.",
    )


def add_parser_insecure(p):
    p.add_argument(
        "-k", "--insecure",
        action="store_false",
        dest="ssl_verify",
        default=NULL,
        help="Allow conda to perform \"insecure\" SSL connections and transfers. "
             "Equivalent to setting 'ssl_verify' to 'false'."
    )
