# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from argparse import ArgumentParser as ArgumentParserBase, RawDescriptionHelpFormatter
import sys

from .common import add_parser_help
from ..exceptions import CommandNotFoundError


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
