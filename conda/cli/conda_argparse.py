
from argparse import *

__ArgumentParser = ArgumentParser

class ArgumentParser(__ArgumentParser):
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
            exc.argument = self._get_action_from_name(exc.argument_name)
            if not exc.argument or exc.argument.dest != "cmd": raise exc
            # this is incredibly lame, but argparse stupidly does not expose reasonable hooks
            # for customizing error handling
            import re
            m = re.compile(r"invalid choice: '(\w+)'").match(exc.message)
            if m:
                cmd = m.group(1)
                msg = "conda: error: %r is not a conda command, see 'conda -h'" % cmd
                from difflib import get_close_matches
                close = get_close_matches(cmd, exc.argument.choices.keys())
                if close:
                    msg += '\n\nDid you mean one of these?\n\n'
                    for s in close:
                        msg += '    %s' % s
                    msg += "\n"
                exc.message = msg
            raise exc
        super(ArgumentParser, self).error(message)

del __ArgumentParser
