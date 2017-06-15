# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import timedelta
import json
from logging import getLogger
import os
import sys
from traceback import format_exc

from . import CondaError, CondaExitZero, CondaMultiError, text_type
from ._vendor.auxlib.entity import EntityEncoder
from ._vendor.auxlib.ish import dals
from ._vendor.auxlib.type_coercion import boolify
from .base.constants import PathConflict
from .common.compat import ensure_text_type, input, iteritems, iterkeys, on_win, string_types
from .common.io import timeout
from .common.signals import get_signal_name
from .common.url import maybe_unquote

try:
    from cytoolz.itertoolz import groupby
except ImportError:  # pragma: no cover
    from ._vendor.toolz.itertoolz import groupby  # NOQA

log = getLogger(__name__)


class LockError(CondaError):
    def __init__(self, message):
        msg = "%s" % message
        super(LockError, self).__init__(msg)


class ArgumentError(CondaError):
    def __init__(self, message, **kwargs):
        super(ArgumentError, self).__init__(message, **kwargs)


class CommandArgumentError(ArgumentError):
    def __init__(self, message, **kwargs):
        command = ' '.join(ensure_text_type(s) for s in sys.argv)
        super(CommandArgumentError, self).__init__(message, command=command, **kwargs)


class CondaSignalInterrupt(CondaError):
    def __init__(self, signum):
        signal_name = get_signal_name(signum)
        super(CondaSignalInterrupt, self).__init__("Signal interrupt %(signal_name)s",
                                                   signal_name=signal_name,
                                                   signum=signum)


class TooManyArgumentsError(ArgumentError):
    def __init__(self, expected, received, offending_arguments, optional_message='',
                 *args):
        self.expected = expected
        self.received = received
        self.offending_arguments = offending_arguments
        self.optional_message = optional_message

        suffix = 's' if received - expected > 1 else ''
        msg = ('%s Got %s argument%s (%s) but expected %s.' %
               (optional_message, received, suffix, ', '.join(offending_arguments), expected))
        super(TooManyArgumentsError, self).__init__(msg, *args)


class TooFewArgumentsError(ArgumentError):
    def __init__(self, expected, received, optional_message='', *args):
        self.expected = expected
        self.received = received
        self.optional_message = optional_message

        msg = ('%s Got %s arguments but expected %s.' %
               (optional_message, received, expected))
        super(TooFewArgumentsError, self).__init__(msg, *args)


class ClobberError(CondaError):
    def __init__(self, message, path_conflict, **kwargs):
        self.path_conflict = path_conflict
        super(ClobberError, self).__init__(message, **kwargs)

    def __repr__(self):
        clz_name = "ClobberWarning" if self.path_conflict == PathConflict.warn else "ClobberError"
        return '%s: %s\n' % (clz_name, text_type(self))


class BasicClobberError(ClobberError):
    def __init__(self, source_path, target_path, context):
        message = dals("""
        Conda was asked to clobber an existing path.
          source path: %(source_path)s
          target path: %(target_path)s
        """)
        if context.path_conflict == PathConflict.prevent:
            message += ("Conda no longer clobbers existing paths without the use of the "
                        "--clobber option\n.")
        super(BasicClobberError, self).__init__(message, context.path_conflict,
                                                target_path=target_path,
                                                source_path=source_path)


class KnownPackageClobberError(ClobberError):
    def __init__(self, target_path, colliding_dist_being_linked, colliding_linked_dist, context):
        message = dals("""
        The package '%(colliding_dist_being_linked)s' cannot be installed due to a
        path collision for '%(target_path)s'.
        This path already exists in the target prefix, and it won't be removed by
        an uninstall action in this transaction. The path appears to be coming from
        the package '%(colliding_linked_dist)s', which is already installed in the prefix.
        """)
        if context.path_conflict == PathConflict.prevent:
            message += ("If you'd like to proceed anyway, re-run the command with "
                        "the `--clobber` flag.\n.")
        super(KnownPackageClobberError, self).__init__(
            message, context.path_conflict,
            target_path=target_path,
            colliding_dist_being_linked=colliding_dist_being_linked,
            colliding_linked_dist=colliding_linked_dist,
        )


class UnknownPackageClobberError(ClobberError):
    def __init__(self, target_path, colliding_dist_being_linked, context):
        message = dals("""
        The package '%(colliding_dist_being_linked)s' cannot be installed due to a
        path collision for '%(target_path)s'.
        This path already exists in the target prefix, and it won't be removed
        by an uninstall action in this transaction. The path is one that conda
        doesn't recognize. It may have been created by another package manager.
        """)
        if context.path_conflict == PathConflict.prevent:
            message += ("If you'd like to proceed anyway, re-run the command with "
                        "the `--clobber` flag.\n.")
        super(UnknownPackageClobberError, self).__init__(
            message, context.path_conflict,
            target_path=target_path,
            colliding_dist_being_linked=colliding_dist_being_linked,
        )


class SharedLinkPathClobberError(ClobberError):
    def __init__(self, target_path, incompatible_package_dists, context):
        message = dals("""
        This transaction has incompatible packages due to a shared path.
          packages: %(incompatible_packages)s
          path: '%(target_path)s'
        """)
        if context.path_conflict == PathConflict.prevent:
            message += ("If you'd like to proceed anyway, re-run the command with "
                        "the `--clobber` flag.\n.")
        super(SharedLinkPathClobberError, self).__init__(
            message, context.path_conflict,
            target_path=target_path,
            incompatible_packages=', '.join(text_type(d) for d in incompatible_package_dists),
        )


class CommandNotFoundError(CondaError):
    def __init__(self, command):
        build_commands = {
            'build',
            'convert',
            'develop',
            'index',
            'inspect',
            'metapackage',
            'render',
            'skeleton',
        }
        needs_source = {
            'activate',
            'deactivate'
        }
        if command in build_commands:
            message = dals("""
            You need to install conda-build in order to
            use the 'conda %(command)s' command.
            """)
        elif command in needs_source and not on_win:
            message = dals("""
            '%(command)s is not a conda command.
            Did you mean 'source %(command)s'?
            """)
        else:
            message = "'%(command)s'"
        super(CommandNotFoundError, self).__init__(message, command=command)


class PathNotFoundError(CondaError, OSError):
    def __init__(self, path):
        message = "%(path)s"
        super(PathNotFoundError, self).__init__(message, path=path)


class DirectoryNotFoundError(CondaError):
    def __init__(self, path):
        message = "%(path)s"
        super(DirectoryNotFoundError, self).__init__(message, path=path)


class EnvironmentLocationNotFound(CondaError):
    def __init__(self, location):
        message = "Not a conda environment: %(location)s"
        super(EnvironmentLocationNotFound, self).__init__(message, location=location)


class EnvironmentNameNotFound(CondaError):
    def __init__(self, environment_name):
        message = dals("""
        Could not find conda environment: %(environment_name)s
        You can list all discoverable environments with `conda info --envs`.
        """)
        super(EnvironmentNameNotFound, self).__init__(message, environment_name=environment_name)


class CondaEnvironmentError(CondaError, EnvironmentError):
    def __init__(self, message, *args):
        msg = '%s' % message
        super(CondaEnvironmentError, self).__init__(msg, *args)


class DryRunExit(CondaExitZero):
    def __init__(self):
        msg = 'Dry run exiting'
        super(DryRunExit, self).__init__(msg)


class CondaSystemExit(CondaExitZero, SystemExit):
    def __init__(self, *args):
        msg = ' '.join(text_type(arg) for arg in self.args)
        super(CondaSystemExit, self).__init__(msg)


class SubprocessExit(CondaExitZero):
    def __init__(self, *args, **kwargs):
        super(SubprocessExit, self).__init__(*args, **kwargs)


class PaddingError(CondaError):
    def __init__(self, dist, placeholder, placeholder_length):
        msg = ("Placeholder of length '%d' too short in package %s.\n"
               "The package must be rebuilt with conda-build > 2.0." % (placeholder_length, dist))
        super(PaddingError, self).__init__(msg)


class LinkError(CondaError):
    def __init__(self, message):
        super(LinkError, self).__init__(message)


class CondaOSError(CondaError, OSError):
    def __init__(self, message):
        msg = '%s' % message
        super(CondaOSError, self).__init__(msg)


class ProxyError(CondaError):
    def __init__(self, message):
        msg = '%s' % message
        super(ProxyError, self).__init__(msg)


class CondaIOError(CondaError, IOError):
    def __init__(self, message, *args):
        msg = '%s' % message
        super(CondaIOError, self).__init__(msg)


class CondaFileIOError(CondaIOError):
    def __init__(self, filepath, message, *args):
        self.filepath = filepath

        msg = "'%s'. %s" % (filepath, message)
        super(CondaFileIOError, self).__init__(msg, *args)


class CondaKeyError(CondaError, KeyError):
    def __init__(self, key, message, *args):
        self.key = key
        self.msg = "'%s': %s" % (key, message)
        super(CondaKeyError, self).__init__(self.msg, *args)


class ChannelError(CondaError):
    def __init__(self, message, *args):
        msg = '%s' % message
        super(ChannelError, self).__init__(msg)


class ChannelNotAllowed(ChannelError):
    def __init__(self, message, *args):
        msg = '%s' % message
        super(ChannelNotAllowed, self).__init__(msg, *args)


class CondaImportError(CondaError, ImportError):
    def __init__(self, message):
        msg = '%s' % message
        super(CondaImportError, self).__init__(msg)


class ParseError(CondaError):
    def __init__(self, message):
        msg = '%s' % message
        super(ParseError, self).__init__(msg)


class CouldntParseError(ParseError):
    def __init__(self, reason):
        self.reason = reason
        super(CouldntParseError, self).__init__(self.args[0])


class MD5MismatchError(CondaError):
    def __init__(self, url, target_full_path, expected_md5sum, actual_md5sum):
        message = dals("""
        Conda detected a mismatch between the expected content and downloaded content
        for url '%(url)s'.
          download saved to: %(target_full_path)s
          expected md5 sum: %(expected_md5sum)s
          actual md5 sum: %(actual_md5sum)s
        """)
        url = maybe_unquote(url)
        super(MD5MismatchError, self).__init__(message, url=url, target_full_path=target_full_path,
                                               expected_md5sum=expected_md5sum,
                                               actual_md5sum=actual_md5sum)


class PackageNotFoundError(CondaError):
    def __init__(self, message, **kwargs):
        super(PackageNotFoundError, self).__init__(message, **kwargs)


class PackageNotInstalledError(PackageNotFoundError):

    def __init__(self, prefix, package_name):
        message = dals("""
        Package is not installed in prefix.
          prefix: %(prefix)s
          package name: %(package_name)s
        """)
        super(PackageNotInstalledError, self).__init__(message, prefix=prefix,
                                                       package_name=package_name)


class CondaHTTPError(CondaError):
    def __init__(self, message, url, status_code, reason, elapsed_time, response=None,
                 caused_by=None):
        _message = dals("""
        HTTP %(status_code)s %(reason)s for url <%(url)s>
        Elapsed: %(elapsed_time)s
        """)
        cf_ray = getattr(response, 'headers', {}).get('CF-RAY')
        _message += "CF-RAY: %s\n\n" % cf_ray if cf_ray else "\n"
        message = _message + message

        from ._vendor.auxlib.logz import stringify
        response_details = (stringify(response) or '') if response else ''

        url = maybe_unquote(url)
        if isinstance(elapsed_time, timedelta):
            elapsed_time = text_type(elapsed_time).split(':', 1)[-1]
        if isinstance(reason, string_types):
            reason = reason.upper()
        super(CondaHTTPError, self).__init__(message, url=url, status_code=status_code,
                                             reason=reason, elapsed_time=elapsed_time,
                                             response_details=response_details,
                                             caused_by=caused_by)


class CondaRevisionError(CondaError):
    def __init__(self, message):
        msg = "%s." % message
        super(CondaRevisionError, self).__init__(msg)


class AuthenticationError(CondaError):
    pass


class NoPackagesFoundError(CondaError):
    """An exception to report that requested packages are missing.

    Args:
        bad_deps: a list of tuples of MatchSpecs, assumed to be dependency
        chains, from top level to bottom.

    Returns:
        Raises an exception with a formatted message detailing the
        missing packages and/or dependencies.
    """

    def __init__(self, bad_deps):
        from .resolve import dashlist
        from .base.context import context

        deps = set(q[-1] for q in bad_deps)
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


class UnsatisfiableError(CondaError):
    """An exception to report unsatisfiable dependencies.

    Args:
        bad_deps: a list of tuples of objects (likely MatchSpecs).
        chains: (optional) if True, the tuples are interpreted as chains
            of dependencies, from top level to bottom. If False, the tuples
            are interpreted as simple lists of conflicting specs.

    Returns:
        Raises an exception with a formatted message detailing the
        unsatisfiable specifications.
    """

    def __init__(self, bad_deps, chains=True):
        from .models.match_spec import MatchSpec
        from .resolve import dashlist

        # Remove any target values from the MatchSpecs, convert to strings
        bad_deps = [list(map(lambda x: str(MatchSpec(x, target=None)), dep)) for dep in bad_deps]
        if chains:
            chains = {}
            for dep in sorted(bad_deps, key=len, reverse=True):
                dep1 = [s.partition(' ') for s in dep[1:]]
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
        msg = '%s' % message
        super(InstallError, self).__init__(msg)


class RemoveError(CondaError):
    def __init__(self, message):
        msg = '%s' % message
        super(RemoveError, self).__init__(msg)


class CondaIndexError(CondaError, IndexError):
    def __init__(self, message):
        msg = '%s' % message
        super(CondaIndexError, self).__init__(msg)


class CondaValueError(CondaError, ValueError):
    def __init__(self, message, *args):
        msg = '%s' % message
        super(CondaValueError, self).__init__(msg)


class CondaTypeError(CondaError, TypeError):
    def __init__(self, expected_type, received_type, optional_message):
        msg = "Expected type '%s' and got type '%s'. %s"
        super(CondaTypeError, self).__init__(msg)


class CondaHistoryError(CondaError):
    def __init__(self, message):
        msg = '%s' % message
        super(CondaHistoryError, self).__init__(msg)


class CondaUpgradeError(CondaError):
    def __init__(self, message):
        msg = "%s" % message
        super(CondaUpgradeError, self).__init__(msg)


class CondaVerificationError(CondaError):
    def __init__(self, message):
        super(CondaVerificationError, self).__init__(message)


class NotWritableError(CondaError):

    def __init__(self, path):
        kwargs = {
            'path': path,
        }
        if on_win:
            message = dals("""
            The current user does not have write permissions to a required path.
              path: %(path)s
            """)
        else:
            message = dals("""
            The current user does not have write permissions to a required path.
              path: %(path)s
              uid: %(uid)s
              gid: %(gid)s

            If you feel that permissions on this path are set incorrectly, you can manually
            change them by executing

              $ sudo chmod %(uid)s:%(gid)s %(path)s
            """)
            import os
            kwargs.update({
                'uid': os.geteuid(),
                'gid': os.getegid(),
            })
        super(NotWritableError, self).__init__(message, **kwargs)


class CondaDependencyError(CondaError):
    def __init__(self, message):
        super(CondaDependencyError, self).__init__(message)


class BinaryPrefixReplacementError(CondaError):
    def __init__(self, path, placeholder, new_prefix, original_data_length, new_data_length):
        message = dals("""
        Refusing to replace mismatched data length in binary file.
          path: %(path)s
          placeholder: %(placeholder)s
          new prefix: %(new_prefix)s
          original data Length: %(original_data_length)d
          new data length: %(new_data_length)d
        """)
        kwargs = {
            'path': path,
            'placeholder': placeholder,
            'new_prefix': new_prefix,
            'original_data_length': original_data_length,
            'new_data_length': new_data_length,
        }
        super(BinaryPrefixReplacementError, self).__init__(message, **kwargs)


class InvalidVersionSpecError(CondaError):
    def __init__(self, invalid_spec):
        message = "Invalid version spec: %(invalid_spec)s"
        super(InvalidVersionSpecError, self).__init__(message, invalid_spec=invalid_spec)


def print_conda_exception(exception):
    from .base.context import context

    stdoutlogger = getLogger('stdout')
    stderrlogger = getLogger('stderr')
    if context.json:
        import json
        stdoutlogger.info(json.dumps(exception.dump_map(), indent=2, sort_keys=True,
                                     cls=EntityEncoder))
    else:
        stderrlogger.info("\n%r", exception)


def print_unexpected_error_message(e):
    try:
        traceback = format_exc()
    except AttributeError:  # pragma: no cover
        if sys.version_info[:2] == (3, 4):
            # AttributeError: 'NoneType' object has no attribute '__context__'
            traceback = ''
        else:
            raise

    from .base.context import context

    # bomb = "\U0001F4A3 "
    # explosion = "\U0001F4A5 "
    # fire = "\U0001F525 "
    # print("%s  %s  %s" % (3*bomb, 3*explosion, 3*fire))

    command = ' '.join(ensure_text_type(s) for s in sys.argv)
    info_dict = {}
    if ' info' not in command:
        try:
            from .cli.main_info import get_info_dict
            info_dict = get_info_dict()
        except Exception as info_e:
            info_traceback = format_exc()
            info_dict = {
                'error': repr(info_e),
                'error_type': info_e.__class__.__name__,
                'traceback': info_traceback,
            }

    error_report = {
        'error': repr(e),
        'error_type': e.__class__.__name__,
        'command': command,
        'traceback': traceback,
        'conda_info': info_dict,
    }

    try:
        isatty = os.isatty(0) or on_win
    except Exception as e:
        log.debug('%r', e)
        # given how the rest of this function is constructed, better to assume True here
        isatty = True

    if context.report_errors is False:
        ask_for_upload = False
        do_upload = False
    elif context.report_errors is True or context.always_yes:
        ask_for_upload = False
        do_upload = True
    elif context.json or context.quiet:
        ask_for_upload = False
        do_upload = not context.offline and context.always_yes
    elif not isatty:
        ask_for_upload = False
        do_upload = not context.offline and context.always_yes
    else:
        ask_for_upload = True
        do_upload = False

    stdin = None
    if context.json:
        from .cli.common import stdout_json
        stdout_json(error_report)
    else:
        message_builder = []
        if not ask_for_upload:
            message_builder.append(
                "An unexpected error has occurred. Conda has prepared the following report."
            )
        message_builder.append('')
        message_builder.append('`$ %s`' % command)
        message_builder.append('')
        message_builder.extend('    ' + line for line in traceback.splitlines())
        message_builder.append('')
        if info_dict:
            from .cli.main_info import get_main_info_str
            try:
                message_builder.append(get_main_info_str(info_dict))
            except Exception as e:
                message_builder.append('conda info could not be constructed.')
                message_builder.append('%r' % e)
        message_builder.append('')

        if ask_for_upload:
            message_builder.append(
                "An unexpected error has occurred. Conda has prepared the above report."
            )
            message_builder.append(
                "Would you like conda to send this report to the core maintainers?"
            )
            message_builder.append(
                "[y/N]: "
            )
        sys.stderr.write('\n'.join(message_builder))
        if ask_for_upload:
            try:
                stdin = timeout(40, input)
                do_upload = stdin and boolify(stdin)

            except Exception as e:  # pragma: no cover
                log.debug('%r', e)
                do_upload = False

    if do_upload:
        headers = {
            'User-Agent': context.user_agent,
        }
        _timeout = context.remote_connect_timeout_secs, context.remote_read_timeout_secs
        data = json.dumps(error_report, sort_keys=True, cls=EntityEncoder) + '\n'
        try:
            # requests does not follow HTTP standards for redirects of non-GET methods
            # That is, when following a 301 or 302, it turns a POST into a GET.
            # And no way to disable.  WTF
            import requests
            response = requests.head(context.error_upload_url, headers=headers, timeout=_timeout)
            location = response.headers.get('Location', context.error_upload_url)
            response = requests.post(location, headers=headers, timeout=_timeout, data=data)
            log.debug("upload response status: %s", response and response.status_code)
        except Exception as e:  # pragma: no cover
            log.info('%r', e)

        if stdin:
            sys.stderr.write(
                "\n"
                "Thank you for helping to improve conda.\n"
                "Opt-in to always sending reports (and not see this message again)\n"
                "by running\n"
                "\n"
                "    $ conda config --set report_errors true\n"
                "\n"
            )
    elif ask_for_upload and stdin is None:
        # means timeout was reached for `input`
        sys.stderr.write('\nTimeout reached. No report sent.\n')
    elif ask_for_upload:
        sys.stderr.write(
            "\n"
            "No report sent. To permanently opt-out, use\n"
            "\n"
            "    $ conda config --set report_errors false\n"
            "\n"
        )


def maybe_raise(error, context):
    if isinstance(error, CondaMultiError):
        groups = groupby(lambda e: isinstance(e, ClobberError), error.errors)
        clobber_errors = groups.get(True, ())
        non_clobber_errors = groups.get(False, ())
        if clobber_errors:
            if context.path_conflict == PathConflict.prevent and not context.clobber:
                raise error
            elif context.path_conflict == PathConflict.warn and not context.clobber:
                print_conda_exception(CondaMultiError(clobber_errors))
        if non_clobber_errors:
            raise CondaMultiError(non_clobber_errors)
    elif isinstance(error, ClobberError):
        if context.path_conflict == PathConflict.prevent and not context.clobber:
            raise error
        elif context.path_conflict == PathConflict.warn and not context.clobber:
            print_conda_exception(error)
    else:
        raise error


def handle_exception(e):
    return_code = getattr(e, 'return_code', None)
    if return_code == 0:
        return 0
    elif isinstance(e, CondaError):
        from .base.context import context
        if context.debug or context.verbosity > 0:
            sys.stderr.write('%r\n' % e)
            sys.stderr.write(format_exc())
            sys.stderr.write('\n')
        else:
            print_conda_exception(e)
        return return_code if return_code else 1
    else:
        print_unexpected_error_message(e)
        return return_code if return_code else 1


def conda_exception_handler(func, *args, **kwargs):
    try:
        return_value = func(*args, **kwargs)
        if isinstance(return_value, int):
            return return_value
    except Exception as e:
        return handle_exception(e)
