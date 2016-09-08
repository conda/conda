# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import os
import sys
from conda._vendor.auxlib.entity import EntityEncoder
from logging import getLogger
from traceback import format_exc

from . import CondaError, text_type
from .compat import iteritems, iterkeys
log = logging.getLogger(__name__)

class LockError(CondaError, RuntimeError):
    def __init__(self, message):
        msg = "Lock error: %s" % message
        super(LockError, self).__init__(msg)


class ArgumentError(CondaError):
    def __init__(self, message, **kwargs):
        super(ArgumentError, self).__init__(message, **kwargs)


class CommandArgumentError(ArgumentError):
    def __init__(self, message, **kwargs):
        command = ' '.join(sys.argv)
        super(CommandArgumentError, self).__init__(message, command=command, **kwargs)


class ArgumentNotFoundError(ArgumentError):
    def __init__(self, argument, *args):
        self.argument = argument
        msg = 'Argument not found: %s. %s' \
              % (argument, ' '.join(text_type(arg) for arg in self.args))
        super(ArgumentNotFoundError, self).__init__(msg)


class TooManyArgumentsError(ArgumentError):
    def __init__(self, expected, received, offending_arguments, optional_message='',
                 *args):
        self.expected = expected
        self.received = received
        self.offending_arguments = offending_arguments
        self.optional_message = optional_message

        suffix = 's' if received - expected > 1 else ''
        msg = ('Too many arguments: %s. Got %s argument%s (%s) and expected %s.' %
               (optional_message, received, suffix, ', '.join(offending_arguments), expected))
        super(TooManyArgumentsError, self).__init__(msg, *args)


class TooFewArgumentsError(ArgumentError):
    def __init__(self, expected, received, optional_message='', *args):
        self.expected = expected
        self.received = received
        self.optional_message = optional_message

        msg = 'Too few arguments: %s. Got %s arguments and expected %s.' %\
              (optional_message, received, expected)
        super(TooFewArgumentsError, self).__init__(msg, *args)


class CommandError(CondaError):
    def __init__(self, command, message):
        self.command = command
        extra_info = ' '.join(text_type(arg) for arg in self.args)
        msg = "Command Error: error with command '%s'. %s %s" % (command, message, extra_info)
        super(CommandError, self).__init__(msg)


class CommandNotFoundError(CommandError):
    def __init__(self, command, message):
        self.command = command
        msg = "Command not found: '%s'. %s" % (command, message)
        super(CommandNotFoundError, self).__init__(command, msg)


class CondaFileNotFoundError(CondaError, OSError):
    def __init__(self, filename, *args):
        self.filename = filename
        msg = "File not found: '%s'." % filename
        super(CondaFileNotFoundError, self).__init__(msg, *args)


class DirectoryNotFoundError(CondaError):
    def __init__(self, directory, message, *args):
        self.directory = directory
        msg = 'Directory not found: %s' % directory
        super(DirectoryNotFoundError, self).__init__(msg)


class CondaEnvironmentNotFoundError(CondaError, EnvironmentError):
    """ Raised when a requested environment cannot be found.

    args:
        environment_name_or_prefix (str): either the name or location of an environment
    """
    def __init__(self, environment_name_or_prefix, *args, **kwargs):
        msg = ("Could not find environment: %s .\n"
               "You can list all discoverable environments with `conda info --envs`."
               % environment_name_or_prefix)
        self.environment_name_or_prefix = environment_name_or_prefix
        super(CondaEnvironmentNotFoundError, self).__init__(msg, *args, **kwargs)


class CondaEnvironmentError(CondaError, EnvironmentError):
    def __init__(self, message, *args):
        msg = 'Environment error: %s' % message
        super(CondaEnvironmentError, self).__init__(msg, *args)


class DryRunExit(CondaError):
    def __init__(self, message):
        msg = 'Dry run exiting: %s' % message
        super(DryRunExit, self).__init__(msg)


class CondaSystemExit(CondaError, SystemExit):
    def __init__(self, *args):
        msg = ' '.join(text_type(arg) for arg in self.args)
        super(CondaSystemExit, self).__init__(msg)


class SubprocessExit(CondaError):
    def __init__(self, *args, **kwargs):
        super(SubprocessExit, self).__init__(*args, **kwargs)


class PaddingError(CondaError):
    def __init__(self, *args):
        msg = 'Padding error: %s' % ' '.join(text_type(arg) for arg in self.args)
        super(PaddingError, self).__init__(msg)


class LinkError(CondaError):
    def __init__(self, message):
        msg = 'Link error: %s ' % message
        super(LinkError, self).__init__(msg)


class CondaOSError(CondaError, OSError):
    def __init__(self, message):
        msg = 'OS error: %s' % message
        super(CondaOSError, self).__init__(msg)


class ProxyError(CondaError):
    def __init__(self, message):
        msg = 'Proxy error: %s' % message
        super(ProxyError, self).__init__(msg)


class CondaIOError(CondaError, IOError):
    def __init__(self, message, *args):
        msg = 'IO error: %s' % message
        super(CondaIOError, self).__init__(msg)


class CondaFileIOError(CondaIOError):
    def __init__(self, filepath, message, *args):
        self.filepath = filepath

        msg = "Couldn't read or write to file. '%s'. %s" % (filepath, message)
        super(CondaFileIOError, self).__init__(msg, *args)


class CondaKeyError(CondaError, KeyError):
    def __init__(self, key, message, *args):
        self.key = key

        self.msg = "Error with key '%s': %s" % (key, message)
        super(CondaKeyError, self).__init__(self.msg, *args)


class ChannelError(CondaError):
    def __init__(self, message, *args):
        msg = 'Channel Error: %s' % message
        super(ChannelError, self).__init__(msg)


class ChannelNotAllowed(ChannelError):
    def __init__(self, message, *args):
        msg = 'Channel not allowed: %s' % message
        super(ChannelNotAllowed, self).__init__(msg, *args)


class CondaImportError(CondaError, ImportError):
    def __init__(self, message):
        msg = 'Import error: %s' % message
        super(CondaImportError, self).__init__(msg)


class ParseError(CondaError):
    def __init__(self, message):
        msg = 'Parse error: %s' % message
        super(ParseError, self).__init__(msg)


class CouldntParseError(ParseError):
    def __init__(self, reason):
        self.reason = reason
        super(CouldntParseError, self).__init__(self.args[0])


class MD5MismatchError(CondaError):
    def __init__(self, message):
        msg = 'MD5MismatchError: %s' % message
        super(MD5MismatchError, self).__init__(msg)


class PackageNotFoundError(CondaError):
    def __init__(self, package_name, message, *args):
        self.package_name = package_name
        msg = "Package not found: '%s' %s" % (package_name, message)
        super(PackageNotFoundError, self).__init__(msg)


class CondaHTTPError(CondaError):
    def __init__(self, message):
        msg = 'HTTP Error: %s' % message
        super(CondaHTTPError, self).__init__(msg)


class CondaRevisionError(CondaError):
    def __init__(self, message):
        msg = 'Revision Error :%s' % message
        super(CondaRevisionError, self).__init__(msg)


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
    def __init__(self, bad_deps):
        from .resolve import dashlist
        from .base.context import context

        deps = set(q[-1].spec for q in bad_deps)
        if all(len(q) > 1 for q in bad_deps):
            what = "Dependencies" if len(bad_deps) > 1 else "Dependency"
        elif all(len(q) == 1 for q in bad_deps):
            what = "Packages" if len(bad_deps) > 1 else "Package"
        else:
            what = "Packages/dependencies"
        bad_deps = dashlist(' -> '.join(map(str, q)) for q in bad_deps)
        msg = '%s missing in current %s channels: %s' % (what, context.subdir, bad_deps)
        super(NoPackagesFoundError, self).__init__(msg)
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
    def __init__(self, bad_deps, chains=True):
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
        msg = msg % dashlist(bad_deps)
        super(UnsatisfiableError, self).__init__(msg)


class InstallError(CondaError):
    def __init__(self, message):
        msg = 'Install error: %s' % message
        super(InstallError, self).__init__(msg)


class RemoveError(CondaError):
    def __init__(self, message):
        msg = 'Remove Error: %s' % message
        super(RemoveError, self).__init__(msg)


class CondaIndexError(CondaError, IndexError):
    def __init__(self, message):
        msg = 'Index error: %s' % message
        super(CondaIndexError, self).__init__(msg)


class CondaRuntimeError(CondaError, RuntimeError):
    def __init__(self, message):
        msg = 'Runtime error: %s' % message
        super(CondaRuntimeError, self).__init__(msg)


class CondaValueError(CondaError, ValueError):
    def __init__(self, message, *args):
        msg = 'Value error: %s' % message
        super(CondaValueError, self).__init__(msg)


class CondaTypeError(CondaError, TypeError):
    def __init__(self, expected_type, received_type, optional_message):
        msg = "Type error: expected type '%s' and got type '%s'. %s"
        super(CondaTypeError, self).__init__(msg)


class CondaAssertionError(CondaError, AssertionError):
    def __init__(self, message):
        msg = 'Assertion error: %s' % message
        super(CondaAssertionError, self).__init__(msg)


class CondaHistoryError(CondaError):
    def __init__(self, message):
        msg = 'History error: %s' % message
        super(CondaHistoryError, self).__init__(msg)


class CondaSignatureError(CondaError):
    def __init__(self, message):
        msg = 'Signature error: %s' % message
        super(CondaSignatureError, self).__init__(msg)


def print_conda_exception(exception):
    from conda.base.context import context

    stdoutlogger = getLogger('stdout')
    stderrlogger = getLogger('stderr')

    if context.json:
        import json
        # stdoutlogger.info('https://anaconda.org/t/fjffjelk3jl4TGEGGjl343/username/package/')
        # stdoutlogger.info('https://hello.world.com/t/fjffjelk3jl4TGEGGjl343/username/package/')
        # stdoutlogger.info('https://helloworld.com/t/fjffjelk3jl4TGEGGjl343/username/package/')
        # stdoutlogger.info('http://helloworld.com/t/fjffjelk3jl4TGEGGjl343/username/package/')
        # stdoutlogger.info('http://helloworld.com:8888/t/fjffjelk3jl4TGEGGjl343/username/package/')
        stdoutlogger.info(json.dumps(exception.dump_map(), indent=2, sort_keys=True,
                                     cls=EntityEncoder))
    else:
        stderrlogger.info(repr(exception))

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
    # bomb = "\U0001F4A3 "
    # explosion = "\U0001F4A5 "
    # fire = "\U0001F525 "
    # print("%s  %s  %s" % (3*bomb, 3*explosion, 3*fire))
    traceback = format_exc()

    stderrlogger = getLogger('stderr')

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
        stderrlogger.info(message)
        command = ' '.join(sys.argv)
        if ' info' not in command:
            # get and print `conda info`
            info_stdout, info_stderr = get_info()
            stderrlogger.info(info_stdout if info_stdout else info_stderr)
        stderrlogger.info("`$ {0}`".format(command))
        stderrlogger.info('\n')
        stderrlogger.info('\n'.join('    ' + line for line in traceback.splitlines()))


def delete_lock(extra_path=None):
    """
        Delete lock on exception accoding to pid
        log warning when delete fails

        Args:
            extra_path : The extra path that you want to search and
            delete locks
    """
    from .cli.main_clean import find_lock
    from .lock import LOCK_EXTENSION
    from .install import rm_rf
    file_end = "%s.%s" % (os.getpid(), LOCK_EXTENSION)
    locks = list(find_lock(file_ending=file_end, extra_path=extra_path))
    failed_delete = []
    for path in locks:
        try:
            rm_rf(path)
        except (OSError, IOError) as e:
            failed_delete.append(path)
            log.warn("%r Cannot unlink %s.", e, path)

    if failed_delete:
        log.warn("Unable to remove all for this processlocks.\n"
                 "Please run `conda clean --lock`.")


def conda_exception_handler(func, *args, **kwargs):
    try:
        return_value = func(*args, **kwargs)
        if isinstance(return_value, int):
            return return_value
    except CondaRuntimeError as e:
        print_unexpected_error_message(e)
        delete_lock()
        return 1
    except CondaError as e:
        from conda.base.context import context
        if context.debug:
            print_unexpected_error_message(e)
        else:
            print_conda_exception(e)
        delete_lock()
        return 1
    except Exception as e:
        print_unexpected_error_message(e)
        delete_lock()
        return 1
