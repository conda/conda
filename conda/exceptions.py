from __future__ import absolute_import, division, print_function


class CondaException(Exception):
    def __init__(self, *args, **kwargs):
        super(CondaException, self).__init__(*args, **kwargs)


class InvalidInstruction(CondaException):
    def __init__(self, instruction, *args, **kwargs):
        msg = "No handler for instruction: %r" % instruction
        super(InvalidInstruction, self).__init__(msg, *args, **kwargs)


class LockError(CondaException, RuntimeError):
    pass


class ArgumentError(CondaException):
    def __init__(self, message, *args, **kwargs):
        msg = 'Argument Error: %s' % message
        super(ArgumentError, self).__init__(msg, *args, **kwargs)


class ArgumentNotFoundError(ArgumentError):
    def __init__(self, argument, *args, **kwargs):
        msg = 'Argument not found: %r' % argument
        super(ArgumentNotFoundError, self).__init__(msg, *args, **kwargs)


class TooManyArgumentsError(ArgumentError):
    def __init__(self, message, *args, **kwargs):
        msg = 'Too many arguments: %s' % message
        super(TooManyArgumentsError, self).__init__(msg, *args, **kwargs)


class TooFewArgumentsError(ArgumentError):
    def __init__(self, message, *args, **kwargs):
        msg = 'Too few arguments: %s' % message
        super(TooFewArgumentsError, self).__init__(msg, *args, **kwargs)


class CommandError(CondaException):
    def __init__(self, message, *args, **kwargs):
        msg = 'Command Error: %s' % message
        super(CommandError, self).__init__(msg, *args, **kwargs)


class CommandNotFoundError(CommandError):
    def __init__(self, message, *args, **kwargs):
        msg = 'Command not found: %s' % message
        super(CommandNotFoundError, self).__init__(msg, *args, **kwargs)


class CondaFileNotFoundError(CondaException, FileNotFoundError):
    def __init__(self, message, *args, **kwargs):
        msg = "File not found: %s" % message
        super(CondaFileNotFoundError, self).__init__(msg, *args, **kwargs)


class DirectoryNotFoundError(CondaException):
    def __init__(self, message, *args, **kwargs):
        msg = 'Directory not found: %s' % message
        super(DirectoryNotFoundError, self).__init__(msg, *args, **kwargs)


class CondaEnvironmentError(CondaException, EnvironmentError):
    def __init__(self, message, *args, **kwargs):
        msg = 'Environment not found: %s' % message
        super(CondaEnvironmentError, self).__init__(msg, *args, **kwargs)


class DryRunExit(CondaException):
    def __init__(self, *args, **kwargs):
        msg = 'Dry run: exiting'
        super(DryRunExit, self).__init__(msg, *args, **kwargs)


class CondaSystemExit(CondaException, SystemExit):
    def __init__(self, message, *args, **kwargs):
        msg = 'Exiting: %s' % message
        super(CondaSystemExit, self).__init__(msg, *args, **kwargs)


class SubprocessExit(CondaException):
    def __init__(self, *args, **kwargs):
        msg = 'Subprocess exiting: '
        super(SubprocessExit, self).__init__(msg, *args, **kwargs)


class PaddingError(CondaException):
    def __init__(self, *args, **kwargs):
        msg = 'Padding error: '
        super(PaddingError, self).__init__(msg, *args, **kwargs)


class LinkError(CondaException):
    def __init__(self, *args, **kwargs):
        msg = 'Link error: '
        super(LinkError, self).__init__(msg, *args, **kwargs)


class CondaOSError(CondaException, OSError):
    def __init__(self, message, *args, **kwargs):
        msg = 'OS error: %s' % message
        super(CondaOSError, self).__init__(msg, *args, **kwargs)


class AlreadyInitializedError(CondaException):
    def __init__(self, message, *args, **kwargs):
        super(AlreadyInitializedError, self).__init__(message, *args, **kwargs)


class ProxyError(CondaException):
    def __init__(self, message, *args, **kwargs):
        msg = 'Proxy error: %s' % message
        super(ProxyError, self).__init__(msg, *args, **kwargs)


class CondaIOError(CondaException, IOError):
    def __init__(self, message, *args, **kwargs):
        msg = 'IO error: %s' % message
        super(CondaIOError, self).__init__(msg, *args, **kwargs)


class CondaFileIOError(CondaIOError):
    def __init__(self, message, *args, **kwargs):
        msg = "Couldn't read or write to file. %s" % message
        super(CondaFileIOError, self).__init__(msg, *args, **kwargs)


class CondaKeyError(CondaException, KeyError):
    def __init__(self, message, *args, **kwargs):
        msg = 'Key error: '
        super(CondaKeyError, self).__init__(msg, *args, **kwargs)


class ChannelError(CondaException):
    def __init__(self, message, *args, **kwargs):
        msg = 'Channel Error: %s' % message
        super(ChannelError, self).__init__(msg, *args, **kwargs)


class ChannelNotAllowed(ChannelError):
    def __init__(self, message, *args, **kwargs):
        msg = 'Channel not allowed: %s' % message
        super(ChannelNotAllowed, self).__init__(msg, *args, **kwargs)


class CondaImportError(CondaException, ImportError):
    def __init__(self, message, *args, **kwargs):
        msg = 'Import error: %s' % message
        super(CondaImportError, self).__init__(msg, *args, **kwargs)


class ParseError(CondaException):
    def __init__(self, message, *args, **kwargs):
        msg = 'Parse error: %s' % message
        super(ParseError, self).__init__(msg, *args, **kwargs)


class MD5MismatchError(CondaException):
    def __init__(self, message, *args, **kwargs):
        msg = 'MD5MismatchError: %s' % message
        super(MD5MismatchError, self).__init__(msg, *args, **kwargs)


class PackageNotFoundError(CondaException):
    def __init__(self, message, *args, **kwargs):
        msg = 'Package not found: %s' % message
        super(PackageNotFoundError, self).__init__(msg, *args, **kwargs)


class InstallError(CondaException):
    def __init__(self, message, *args, **kwargs):
        msg = 'Install error: %s' % message
        super(InstallError, self).__init__(msg, *args, **kwargs)


class RemoveError(CondaException):
    def __init__(self, message, *args, **kwargs):
        msg = 'RemoveError: %s' % message
        super(RemoveError, self).__init__(msg, *args, **kwargs)


class CondaIndexError(CondaException, IndexError):
    def __init__(self, message, *args, **kwargs):
        msg = 'Index error: %s' % message
        super(RemoveError, self).__init__(msg, *args, **kwargs)


class CondaRuntimeError(CondaException, RuntimeError):
    def __init__(self, message, *args, **kwargs):
        msg = 'Runtime error: %s' % message
        super(CondaRuntimeError, self).__init__(msg, *args, **kwargs)


class CondaValueError(CondaException, ValueError):
    def __init__(self, message, *args, **kwargs):
        msg = 'Value error: %s' % message
        super(CondaValueError, self).__init__(msg, *args, **kwargs)


class CondaTypeError(CondaException, TypeError):
    def __init__(self, message, *args, **kwargs):
        msg = 'Type error: %s' % message
        super(CondaTypeError, self).__init__(msg, *args, **kwargs)


class CondaAssertionError(CondaException, AssertionError):
    def __init__(self, message, *args, **kwargs):
        msg = 'Assertion error: %s' % message
        super(CondaAssertionError, self).__init__(msg, *args, **kwargs)
