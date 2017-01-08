# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import, unicode_literals

import argparse
import os
import subprocess
import sys
from difflib import get_close_matches

from .common import add_parser_help
from .find_commands import find_commands, find_executable
from ..exceptions import CommandNotFoundError

build_commands = {'build', 'index', 'skeleton', 'package', 'metapackage',
                  'pipbuild', 'develop', 'convert'}

_ARGCOMPLETE_DEBUG = False
def debug_argcomplete(msg):
    # To debug this, replace ttys001 with the fd of the terminal you are using
    # (use the `tty` command to find this), and set _ARGCOMPLETE_DEBUG above
    # to True. You can also `export _ARC_DEBUG=1` in the shell you are using
    # to print debug messages from argcomplete.
    if _ARGCOMPLETE_DEBUG:
        f = open('/dev/ttys001', 'w')
        f.write("\n%s\n" % msg)
        f.flush()


try:
    import argcomplete
    argcomplete.CompletionFinder
except (ImportError, AttributeError):
    # On Python 3.3, argcomplete can be an empty namespace package when
    # we are in the conda-recipes directory.
    argcomplete = None

if argcomplete:
    class CondaSubprocessCompletionFinder(argcomplete.CompletionFinder):
        def __call__(self, argument_parser, **kwargs):
            def call_super():
                parent = super(CondaSubprocessCompletionFinder, self)
                return parent.__call__(argument_parser, **kwargs)

            debug_argcomplete("Working")

            if argument_parser.prog != 'conda':
                debug_argcomplete("Argument parser is not conda")
                return call_super()

            environ = os.environ.copy()
            if 'COMP_LINE' not in environ:
                debug_argcomplete("COMP_LINE not in environ")
                return call_super()

            subcommands = find_commands()
            for subcommand in subcommands:
                if 'conda %s' % subcommand in environ['COMP_LINE']:
                    environ['COMP_LINE'] = environ['COMP_LINE'].replace('conda %s' % subcommand,
                                                                        'conda-%s' % subcommand)
                    debug_argcomplete("Using subprocess")
                    debug_argcomplete(sys.argv)
                    import pprint
                    debug_argcomplete(pprint.pformat(environ))
                    args = [find_executable('conda-%s' % subcommand)]
                    debug_argcomplete(args)
                    p = subprocess.Popen(args, env=environ, close_fds=False)
                    p.communicate()
                    sys.exit()
            else:
                debug_argcomplete("Not using subprocess")
                debug_argcomplete(sys.argv)
                debug_argcomplete(argument_parser)
                return call_super()

class ArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        if not kwargs.get('formatter_class'):
            kwargs['formatter_class'] = argparse.RawDescriptionHelpFormatter
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
                        if cmd in build_commands:
                            raise CommandNotFoundError(cmd, '''
Error: You need to install conda-build in order to
use the "conda %s" command.''' % cmd)
                        else:
                            message = "Error: Could not locate 'conda-%s'" % cmd
                            possibilities = (set(argument.choices.keys()) |
                                             build_commands |
                                             set(find_commands()))
                            close = get_close_matches(cmd, possibilities)
                            if close:
                                message += '\n\nDid you mean one of these?\n'
                                for s in close:
                                    message += '    %s' % s
                            raise CommandNotFoundError(cmd, message)

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
other commands, such as "conda build", are available when additional conda
packages (e.g. conda-build) are installed
""")

    def parse_args(self, *args, **kwargs):
        if argcomplete:
            CondaSubprocessCompletionFinder()(self)

        return super(ArgumentParser, self).parse_args(*args, **kwargs)
