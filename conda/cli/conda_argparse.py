# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

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
        import sys
        exc = sys.exc_info()[1]
        if exc:
            # this is incredibly lame, but argparse stupidly does not expose reasonable hooks
            # for customizing error handling
            argument = self._get_action_from_name(exc.argument_name)
            if argument and argument.dest == "cmd":
                import re
                m = re.compile(r"invalid choice: '(\w+)'").match(exc.message)
                if m:
                    cmd = m.group(1)
                    message = "%r is not a conda command, see 'conda -h'" % cmd
                    from difflib import get_close_matches
                    close = get_close_matches(cmd, argument.choices.keys())
                    if close:
                        message += '\n\nDid you mean one of these?\n'
                        for s in close:
                            message += '    %s' % s
                        message += "\n"

        super(ArgumentParser, self).error(message)
