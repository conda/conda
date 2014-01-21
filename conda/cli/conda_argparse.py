# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import sys
import argparse


class ArgumentParser(argparse.ArgumentParser):
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
        from conda.cli.find_commands import find_executable

        exc = sys.exc_info()[1]
        if exc:
            # this is incredibly lame, but argparse stupidly does not expose
            # reasonable hooks for customizing error handling
            if hasattr(exc, 'argument_name'):
                argument = self._get_action_from_name(exc.argument_name)
            else:
                argument = None
            if argument and argument.dest == "cmd":
                m = re.compile(r"invalid choice: '(\w+)'").match(exc.message)
                if m:
                    cmd = m.group(1)
                    executable = find_executable(cmd)
                    if not executable:
                        if cmd == 'build':
                            sys.exit("""\
Error: You need to install conda-build in order to use the 'conda build'
       command.
""")
                        sys.exit("Error: Could not locate 'conda-%s'" % cmd)
                    args = [find_executable(cmd)]
                    args.extend(sys.argv[2:])
                    sys.exit(subprocess.call(args))

        super(ArgumentParser, self).error(message)

    def print_help(self):
        super(ArgumentParser, self).print_help()

        if sys.argv[1:] in ([], ['help'], ['-h'], ['--help']):
            from conda.cli.find_commands import help
            help()
