# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
from traceback import format_exc

from . import CondaError
from .compat import iteritems, iterkeys


class InvalidInstruction(CondaError):
    def __init__(self, instruction, *args, **kwargs):
        msg = "No handler for instruction: %r\n" % instruction
        super(InvalidInstruction, self).__init__(msg, *args, **kwargs)


class LockError(CondaError, RuntimeError):
    def __init__(self, message, *args, **kwargs):
        msg = "Lock error: %s" % message
        super(LockError, self).__init__(msg, *args, **kwargs)


class ArgumentError(CondaError):
    def __init__(self, message, *args, **kwargs):
        msg = 'Argument Error: %s\n' % message
        super(ArgumentError, self).__init__(msg, *args, **kwargs)


class ArgumentNotFoundError(ArgumentError):
    def __init__(self, argument, *args, **kwargs):
        msg = 'Argument not found: %s\n' % argument
        super(ArgumentNotFoundError, self).__init__(msg, *args, **kwargs)


class TooManyArgumentsError(ArgumentError):
    def __init__(self, message, *args, **kwargs):
        msg = 'Too many arguments: %s\n' % message
        super(TooManyArgumentsError, self).__init__(msg, *args, **kwargs)


class TooFewArgumentsError(ArgumentError):
    def __init__(self, message, *args, **kwargs):
        msg = 'Too few arguments: %s\n' % message
        super(TooFewArgumentsError, self).__init__(msg, *args, **kwargs)


class CommandError(CondaError):
    def __init__(self, message, *args, **kwargs):
        msg = 'Command Error: %s\n' % message
        super(CommandError, self).__init__(msg, *args, **kwargs)


class CommandNotFoundError(CommandError):
    def __init__(self, message, *args, **kwargs):
        msg = 'Command not found: %s\n' % message
        super(CommandNotFoundError, self).__init__(msg, *args, **kwargs)


class CondaFileNotFoundError(CondaError, OSError):
    def __init__(self, message, *args, **kwargs):
        msg = "File not found: %s\n" % message
        super(CondaFileNotFoundError, self).__init__(msg, *args, **kwargs)


class DirectoryNotFoundError(CondaError):
    def __init__(self, message, *args, **kwargs):
        msg = 'Directory not found: %s\n' % message
        super(DirectoryNotFoundError, self).__init__(msg, *args, **kwargs)


class CondaEnvironmentError(CondaError, EnvironmentError):
    def __init__(self, message, *args, **kwargs):
        msg = 'Environment not found: %s\n' % message
        super(CondaEnvironmentError, self).__init__(msg, *args, **kwargs)


class DryRunExit(CondaError):
    def __init__(self, *args, **kwargs):
        msg = 'Dry run: exiting\n'
        super(DryRunExit, self).__init__(msg, *args, **kwargs)


class CondaSystemExit(CondaError, SystemExit):
    def __init__(self, *args, **kwargs):
        super(CondaSystemExit, self).__init__(*args, **kwargs)


class SubprocessExit(CondaError):
    def __init__(self, *args, **kwargs):
        msg = 'Subprocess exiting\n'
        super(SubprocessExit, self).__init__(msg, *args, **kwargs)


class PaddingError(CondaError):
    def __init__(self, *args, **kwargs):
        msg = 'Padding error:\n'
        super(PaddingError, self).__init__(msg, *args, **kwargs)


class LinkError(CondaError):
    def __init__(self, *args, **kwargs):
        msg = 'Link error\n'
        super(LinkError, self).__init__(msg, *args, **kwargs)


class CondaOSError(CondaError, OSError):
    def __init__(self, message, *args, **kwargs):
        msg = 'OS error: %s\n' % message
        super(CondaOSError, self).__init__(msg, *args, **kwargs)


class AlreadyInitializedError(CondaError):
    def __init__(self, message, *args, **kwargs):
        msg = message + '\n'
        super(AlreadyInitializedError, self).__init__(msg, *args, **kwargs)


class ProxyError(CondaError):
    def __init__(self, message, *args, **kwargs):
        msg = 'Proxy error: %s\n' % message
        super(ProxyError, self).__init__(msg, *args, **kwargs)


class CondaIOError(CondaError, IOError):
    def __init__(self, message, *args, **kwargs):
        msg = 'IO error: %s\n' % message
        super(CondaIOError, self).__init__(msg, *args, **kwargs)


class CondaFileIOError(CondaIOError):
    def __init__(self, message, *args, **kwargs):
        msg = "Couldn't read or write to file. %s\n" % message
        super(CondaFileIOError, self).__init__(msg, *args, **kwargs)


class CondaKeyError(CondaError, KeyError):
    def __init__(self, message, *args, **kwargs):
        self.msg = 'Key error: %s\n' % message
        super(CondaKeyError, self).__init__(self.msg, *args, **kwargs)


class ChannelError(CondaError):
    def __init__(self, message, *args, **kwargs):
        msg = 'Channel Error: %s\n' % message
        super(ChannelError, self).__init__(msg, *args, **kwargs)


class ChannelNotAllowed(ChannelError):
    def __init__(self, message, *args, **kwargs):
        msg = 'Channel not allowed: %s\n' % message
        super(ChannelNotAllowed, self).__init__(msg, *args, **kwargs)


class CondaImportError(CondaError, ImportError):
    def __init__(self, message, *args, **kwargs):
        msg = 'Import error: %s\n' % message
        super(CondaImportError, self).__init__(msg, *args, **kwargs)


class ParseError(CondaError):
    def __init__(self, message, *args, **kwargs):
        msg = 'Parse error: %s\n' % message
        super(ParseError, self).__init__(msg, *args, **kwargs)


class CouldntParseError(ParseError):
    def __init__(self, reason, *args, **kwargs):
        self.args = ["""Error: Could not parse the yaml file. Use -f to use the
yaml parser (this will remove any structure or comments from the existing
.condarc file). Reason: %s\n""" % reason]
        super(CouldntParseError, self).__init__(self.args[0], *args, **kwargs)

    def __repr__(self):
        return self.args[0]


class MD5MismatchError(CondaError):
    def __init__(self, message, *args, **kwargs):
        msg = 'MD5MismatchError: %s\n' % message
        super(MD5MismatchError, self).__init__(msg, *args, **kwargs)


class PackageNotFoundError(CondaError):
    def __init__(self, message, *args, **kwargs):
        msg = 'Package not found: %s\n' % message
        super(PackageNotFoundError, self).__init__(msg, *args, **kwargs)


class CondaHTTPError(CondaError):
    def __init__(self, message, *args, **kwargs):
        msg = 'HTTP Error: %s\n' % message
        super(CondaHTTPError, self).__init__(msg, *args, **kwargs)


class AuthenticationError(CondaError):
    pass


class NoPackagesFoundError(CondaError, RuntimeError):
    '''An exception to report that requested packages are missing.

    Args:
        bad_deps: a list of tuples of MatchSpecs, assumed to be dependency
        chains, from top level to bottom.

    Returns:
        Raises an exception with a formatted message detailing the
        missing packages and/or dependencies.
    '''
    def __init__(self, bad_deps, *args, **kwargs):
        from .resolve import dashlist
        from .base.context import subdir

        deps = set(q[-1].spec for q in bad_deps)
        if all(len(q) > 1 for q in bad_deps):
            what = "Dependencies" if len(bad_deps) > 1 else "Dependency"
        elif all(len(q) == 1 for q in bad_deps):
            what = "Packages" if len(bad_deps) > 1 else "Package"
        else:
            what = "Packages/dependencies"
        bad_deps = dashlist(' -> '.join(map(str, q)) for q in bad_deps)
        msg = '%s missing in current %s channels: %s\n' % (what, subdir, bad_deps)
        super(NoPackagesFoundError, self).__init__(msg, *args, **kwargs)
        self.pkgs = deps


class UnsatisfiableError(CondaError, RuntimeError):
    '''An exception to report unsatisfiable dependencies.

    Args:
        bad_deps: a list of tuples of objects (likely MatchSpecs).
        chains: (optional) if True, the tuples are interpreted as chains
            of dependencies, from top level to bottom. If False, the tuples
            are interpreted as simple lists of conflicting specs.

    Returns:
        Raises an exception with a formatted message detailing the
        unsatisfiable specifications.
    '''
    def __init__(self, bad_deps, chains=True, *args, **kwargs):
        from .resolve import dashlist, MatchSpec

        bad_deps = [list(map(lambda x: x.spec, dep)) for dep in bad_deps]
        if chains:
            chains = {}
            for dep in sorted(bad_deps, key=len, reverse=True):
                dep1 = [str(MatchSpec(s)).partition(' ') for s in dep[1:]]
                key = (dep[0],) + tuple(v[0] for v in dep1)
                vals = ('',) + tuple(v[2] for v in dep1)
                found = False
                for key2, csets in iteritems(chains):
                    if key2[:len(key)] == key:
                        for cset, val in zip(csets, vals):
                            cset.add(val)
                        found = True
                if not found:
                    chains[key] = [{val} for val in vals]
            bad_deps = []
            for key, csets in iteritems(chains):
                deps = []
                for name, cset in zip(key, csets):
                    if '' not in cset:
                        pass
                    elif len(cset) == 1:
                        cset.clear()
                    else:
                        cset.remove('')
                        cset.add('*')
                    if name[0] == '@':
                        name = 'feature:' + name[1:]
                    deps.append('%s %s' % (name, '|'.join(sorted(cset))) if cset else name)
                chains[key] = ' -> '.join(deps)
            bad_deps = [chains[key] for key in sorted(iterkeys(chains))]
            msg = '''The following specifications were found to be in conflict:%s
Use "conda info <package>" to see the dependencies for each package.'''
        else:
            bad_deps = [sorted(dep) for dep in bad_deps]
            bad_deps = [', '.join(dep) for dep in sorted(bad_deps)]
            msg = '''The following specifications were found to be incompatible with the
others, or with the existing package set:%s
Use "conda info <package>" to see the dependencies for each package.'''
        msg = msg % dashlist(bad_deps) + '\n'
        super(UnsatisfiableError, self).__init__(msg, *args, **kwargs)


class InstallError(CondaError):
    def __init__(self, message, *args, **kwargs):
        msg = 'Install error: %s\n' % message
        super(InstallError, self).__init__(msg, *args, **kwargs)


class RemoveError(CondaError):
    def __init__(self, message, *args, **kwargs):
        msg = 'RemoveError: %s\n' % message
        super(RemoveError, self).__init__(msg, *args, **kwargs)


class CondaIndexError(CondaError, IndexError):
    def __init__(self, message, *args, **kwargs):
        msg = 'Index error: %s\n' % message
        super(CondaIndexError, self).__init__(msg, *args, **kwargs)


class CondaRuntimeError(CondaError, RuntimeError):
    def __init__(self, message, *args, **kwargs):
        msg = 'Runtime error: %s\n' % message
        super(CondaRuntimeError, self).__init__(msg, *args, **kwargs)


class CondaValueError(CondaError, ValueError):
    def __init__(self, message, *args, **kwargs):
        msg = 'Value error: %s\n' % message
        super(CondaValueError, self).__init__(msg, *args, **kwargs)


class CondaTypeError(CondaError, TypeError):
    def __init__(self, message, *args, **kwargs):
        msg = 'Type error: %s\n' % message
        super(CondaTypeError, self).__init__(msg, *args, **kwargs)


class CondaAssertionError(CondaError, AssertionError):
    def __init__(self, message, *args, **kwargs):
        msg = 'Assertion error: %s\n' % message
        super(CondaAssertionError, self).__init__(msg, *args, **kwargs)


class CondaHistoryError(CondaError):
    def __init__(self, message, *args, **kwargs):
        msg = 'History error: %s\n' % message
        super(CondaHistoryError, self).__init__(msg, *args, **kwargs)


class CondaSignatureError(CondaError):
    def __init__(self, message, *args, **kwargs):
        msg = 'Signature error: %s\n' % message
        super(CondaSignatureError, self).__init__(msg, *args, **kwargs)


def print_exception(exception):
    from conda.base.context import context
    from conda.cli.common import stdout_json
    from sys import stderr

    message = repr(exception)

    if context.json:
        stdout_json(dict(error=message))
    else:
        stderr.write(message)


def get_info():
    from conda.cli import conda_argparse
    from conda.cli.main_info import configure_parser
    from shlex import split
    from conda.common.io import captured

    p = conda_argparse.ArgumentParser()
    sub_parsers = p.add_subparsers(metavar='command', dest='cmd')
    configure_parser(sub_parsers)

    args = p.parse_args(split("info"))
    with captured() as c:
        args.func(args, p)
    return c.stdout, c.stderr


def print_unexpected_error_message(e):
    traceback = format_exc()

    from conda.base.context import context
    if context.json:
        from conda.cli.common import stdout_json
        stdout_json(dict(error=traceback))
    else:
        message = """\
An unexpected error has occurred.
Please consider posting the following information to the
conda GitHub issue tracker at:

    https://github.com/conda/conda/issues

"""
        print(message)
        command = ' '.join(sys.argv)
        if ' info' not in command:
            # get and print `conda info`
            info_stdout, info_stderr = get_info()
            print(info_stdout if info_stdout else info_stderr)
        print("`$ {0}`".format(command))
        print('\n')
        print('\n'.join('    ' + line for line in traceback.splitlines()))


def conda_exception_handler(func, *args, **kwargs):
    try:
        return_value = func(*args, **kwargs)
        if isinstance(return_value, int):
            return return_value
    except CondaRuntimeError as e:
        print_unexpected_error_message(e)
        return 1
    except CondaError as e:
        from conda.base.context import context
        if context.debug:
            print_unexpected_error_message(e)
        else:
            print_exception(e)
        return 1
    except Exception as e:
        print_unexpected_error_message(e)
        return 1
