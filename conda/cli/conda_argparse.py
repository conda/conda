# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from argparse import (ArgumentParser as ArgumentParserBase, RawDescriptionHelpFormatter, SUPPRESS,
                      _CountAction, _HelpAction)
import os
import sys

from ..base.context import context
from ..common.constants import NULL


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
        import subprocess
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
                m = re.compile(r"invalid choice: '([\w\-]+)'").match(exc.message)
                if m:
                    cmd = m.group(1)
                    executable = find_executable('conda-' + cmd)
                    if not executable:
                        from ..exceptions import CommandNotFoundError
                        raise CommandNotFoundError(cmd)

                    args = [find_executable('conda-' + cmd)]
                    args.extend(sys.argv[2:])
                    p = subprocess.Popen(args)
                    try:
                        p.communicate()
                    except KeyboardInterrupt:
                        p.wait()
                    finally:
                        sys.exit(p.returncode)

        super(ArgumentParser, self).error(message)

    def print_help(self):
        super(ArgumentParser, self).print_help()

        if self.prog == 'conda' and sys.argv[1:] in ([], ['help'], ['-h'], ['--help']):
            print("""
other commands, such as "conda build", are avaialble when additional conda
packages (e.g. conda-build) are installed
""")


class NullCountAction(_CountAction):

    @staticmethod
    def _ensure_value(namespace, name, value):
        if getattr(namespace, name, NULL) in (NULL, None):
            setattr(namespace, name, value)
        return getattr(namespace, name)

    def __call__(self, parser, namespace, values, option_string=None):
        new_count = self._ensure_value(namespace, self.dest, 0) + 1
        setattr(namespace, self.dest, new_count)


def add_parser_create_install_update(p):
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
    p.add_argument(
        "--clobber",
        action="store_true",
        default=NULL,
        help="Allow clobbering of overlapping file paths within packages, "
             "and suppress related warnings.",
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
        )
    else:  # create or install
        # Same as above except the completer is not only installed packages
        p.add_argument(
            'packages',
            metavar='package_spec',
            action="store",
            nargs='*',
            help="Packages to install into the conda environment.",
        )


def add_parser_pscheck(p):
    p.add_argument(
        "--force-pscheck",
        action="store_true",
        help=("No-op. Included for backwards compatibility (deprecated)."
              if context.platform == 'win' else SUPPRESS)
    )


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
        dest='respect_pinned',
        default=NULL,
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
        help="Name of environment (in %s)." % os.pathsep.join(context.envs_dirs),
        metavar="ENVIRONMENT",
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
        help=SUPPRESS,
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
