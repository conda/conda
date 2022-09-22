# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

from argparse import (
    ArgumentParser as ArgumentParserBase,
    RawDescriptionHelpFormatter,
    Action,
    _CountAction,
)
import os
import sys

from ..common.constants import NULL


class NullCountAction(_CountAction):
    @staticmethod
    def _ensure_value(namespace, name, value):
        if getattr(namespace, name, NULL) in (NULL, None):
            setattr(namespace, name, value)
        return getattr(namespace, name)

    def __call__(self, parser, namespace, values, option_string=None):
        new_count = self._ensure_value(namespace, self.dest, 0) + 1
        setattr(namespace, self.dest, new_count)


class ExtendConstAction(Action):
    # a derivative of _AppendConstAction and Python 3.8's _ExtendAction
    def __init__(
        self,
        option_strings,
        dest,
        const,
        default=None,
        type=None,
        choices=None,
        required=False,
        help=None,
        metavar=None,
    ):
        super().__init__(
            option_strings=option_strings,
            dest=dest,
            nargs="*",
            const=const,
            default=default,
            type=type,
            choices=choices,
            required=required,
            help=help,
            metavar=metavar,
        )

    def __call__(self, parser, namespace, values, option_string=None):
        items = getattr(namespace, self.dest, None)
        items = [] if items is None else items[:]
        items.extend(values or [self.const])
        setattr(namespace, self.dest, items)


class ArgumentParser(ArgumentParserBase):
    def __init__(self, *args, **kwargs):
        if not kwargs.get("formatter_class"):
            kwargs["formatter_class"] = RawDescriptionHelpFormatter
        if "add_help" not in kwargs:
            add_custom_help = True
            kwargs["add_help"] = False
        else:
            add_custom_help = False
        super(ArgumentParser, self).__init__(*args, **kwargs)

        if add_custom_help:
            from .helpers import add_parser_help

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
            if "/".join(action.option_strings) == name:
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
            if hasattr(exc, "argument_name"):
                argument = self._get_action_from_name(exc.argument_name)
            else:
                argument = None
            if argument and argument.dest == "cmd":
                m = re.match(r"invalid choice: u?'([-\w]*?)'", exc.message)
                if m:
                    cmd = m.group(1)
                    if not cmd:
                        self.print_help()
                        sys.exit(0)
                    else:
                        executable = find_executable("conda-" + cmd)
                        if not executable:
                            from ..exceptions import CommandNotFoundError

                            raise CommandNotFoundError(cmd)
                        args = [find_executable("conda-" + cmd)]
                        args.extend(sys.argv[2:])
                        _exec(args, os.environ)

        super(ArgumentParser, self).error(message)

    def print_help(self):
        super(ArgumentParser, self).print_help()

        if sys.argv[1:] in ([], [""], ["help"], ["-h"], ["--help"]):
            from .find_commands import find_commands

            other_commands = find_commands()
            if other_commands:
                builder = [""]
                builder.append("conda commands available from other packages:")
                builder.extend("  %s" % cmd for cmd in sorted(other_commands))
                print("\n".join(builder))
